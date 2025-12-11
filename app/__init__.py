import os

from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from core.configuration.configuration import get_app_version
from core.managers.config_manager import ConfigManager
from core.managers.error_handler_manager import ErrorHandlerManager
from core.managers.logging_manager import LoggingManager
from core.managers.module_manager import ModuleManager

# Load environment variables
load_dotenv()

# Create the instances
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)

# Initialize JWT Manager
jwt = JWTManager()


def create_app(config_name="development"):
    app = Flask(__name__)

    # Load configuration according to environment
    config_manager = ConfigManager(app)
    config_manager.load_config(config_name=config_name)

    # JWT Configuration
    app.config["JWT_SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900  # 15 minutes
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 7 * 24 * 3600  # 7 days

    # Configurar para usar cookies
    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    # If True, only send cookies over HTTPS
    app.config["JWT_COOKIE_SECURE"] = False
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True  # Enable CSRF protection
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"  # 'Lax' or 'Strict' or 'None'
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"
    app.config["JWT_REFRESH_COOKIE_NAME"] = "refresh_token_cookie"
    app.config["JWT_CSRF_IN_COOKIES"] = True  # Store CSRF tokens in cookies
    app.config["JWT_COOKIE_DOMAIN"] = None  # None = same domain as server
    app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
    app.config["JWT_REFRESH_COOKIE_PATH"] = "/"

    # Initialize SQLAlchemy and Migrate with the app
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize Limiter
    limiter.init_app(app)

    # Initialize JWT with the app
    jwt.init_app(app)

    # Register modules
    module_manager = ModuleManager(app)
    module_manager.register_modules()

    # Initialize error handler manager
    error_handler_manager = ErrorHandlerManager(app)
    error_handler_manager.register_error_handlers()

    # Initialize Flask-Mail (simulado cambiar luego)
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USERNAME"] = "astronomiahub@gmail.com"
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_DEFAULT_SENDER"] = "astronomiahub@gmail.com"

    # Initialize Flask-Mail
    mail.init_app(app)

    # Register login manager
    from flask_login import LoginManager

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from app.modules.auth.models import User

        return User.query.get(int(user_id))

    # Set up logging
    logging_manager = LoggingManager(app)
    logging_manager.setup_logging()

    # Initialize error handler manager
    error_handler_manager = ErrorHandlerManager(app)
    error_handler_manager.register_error_handlers()

    # Setting up secret app key for 2FA
    app.secret_key = os.environ["SECRET_KEY"]

    # Injecting environment variables into jinja context
    @app.context_processor
    def inject_vars_into_jinja():
        return {
            "FLASK_APP_NAME": os.getenv("FLASK_APP_NAME"),
            "FLASK_ENV": os.getenv("FLASK_ENV"),
            "DOMAIN": os.getenv("DOMAIN", "localhost"),
            "APP_VERSION": get_app_version(),
        }

    # Initialize JWT blocklist loader
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check if a JWT token has been revoked or expired"""
        from datetime import datetime, timezone

        from app.modules.token.services import TokenService

        jti = jwt_payload.get("jti")
        token_service = TokenService()
        token = token_service.get_token_by_jti(jti)

        if token is None or not token.is_active:
            return True

        if token.expires_at:
            expires_at_aware = token.expires_at
            if expires_at_aware.tzinfo is None:
                expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)

            if expires_at_aware < datetime.now(timezone.utc):
                return True

        return False

    @app.before_request
    def refresh_expired_access_token():
        """Refresh expired access tokens using refresh tokens stored in cookies"""
        from flask import redirect, request, url_for
        from flask_jwt_extended import get_jwt_identity, set_access_cookies, unset_jwt_cookies, verify_jwt_in_request
        from flask_login import logout_user

        from app.modules.token.services import TokenService

        excluded_endpoints = [
            "auth.login",
            "auth.logout",
            "auth.signup",
            "auth.show_signup_form",
            "auth.recover_password",
            "auth.reset_password",
            "auth.login_with_two_factor",
            "auth.two_factor_setup",
            "auth.verify_2fa",
            "auth.verify_2fa_login",
            "auth.scripts",
            "public.index",
            "public.scripts",
            "explore.index",
            "team.index",
            "dataset.subdomain_index",
            "dataset.list_dataset_comments",
            "hubfile.view_file",
            "hubfile.download_file",
            "hubfile.unsave_file",
            "hubfile.save_file",
            "flamapy.check_uvl",
            "flamapy.valid",
            "static",
            "admin.delete_user",
            "profile.author_profile",
            "admin.edit_user",
        ]

        excluded_paths = ["/dataset/file/upload", "/dataset/file/delete", "/dataset/upload", "/recover-password/"]

        if request.endpoint in excluded_endpoints:
            return

        if request.path in excluded_paths:
            return

        if request.is_json or request.path.startswith("/api") or request.path.endswith("/scripts.js"):
            return

        if request.blueprint == "fakenodo" or request.path.startswith("/fakenodo/api"):
            return

        try:
            """First, try to verify the access token"""
            verify_jwt_in_request(locations=["cookies"])
            return
        except Exception:
            try:
                """If access token is invalid, try to verify the refresh token"""
                token_service = TokenService()
                verify_jwt_in_request(locations=["cookies"], refresh=True)

                user_identity = get_jwt_identity()
                user_id = int(user_identity)
                parent_jti = get_jwt()["jti"]

                device_info = token_service.get_device_name_by_request(request) if request else None
                ip_address = TokenService.get_real_ip(request) if request else None
                location_info = TokenService.get_location_by_ip(ip_address) if ip_address else None

                new_access_token = token_service.refresh_access_token(user_id, device_info, location_info, parent_jti)

                response = redirect(request.path)
                set_access_cookies(response, new_access_token)
                return response

            except Exception:
                """If both tokens are invalid, log out the user and redirect to login page"""
                logout_user()
                response = redirect(url_for("auth.login"))
                unset_jwt_cookies(response)
                return response

    return app


app = create_app()
