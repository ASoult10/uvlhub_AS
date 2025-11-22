import os

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from core.configuration.configuration import get_app_version
from core.managers.config_manager import ConfigManager
from core.managers.error_handler_manager import ErrorHandlerManager
from core.managers.logging_manager import LoggingManager
from core.managers.module_manager import ModuleManager
from flask_jwt_extended import JWTManager


from flask_mail import Mail

# Load environment variables
load_dotenv()

# Create the instances
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

# Initialize JWT Manager
jwt = JWTManager()


def create_app(config_name="development"):
    app = Flask(__name__)

    # Load configuration according to environment
    config_manager = ConfigManager(app)
    config_manager.load_config(config_name=config_name)

    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 900  # 15 minutes
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 7 * 24 * 3600  # 7 days
    
    # Configurar para usar cookies
    app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
    app.config['JWT_COOKIE_SECURE'] = False # If True, only send cookies over HTTPS
    app.config['JWT_COOKIE_CSRF_PROTECT'] = True # Enable CSRF protection
    app.config['JWT_COOKIE_SAMESITE'] = 'Lax' # 'Lax' or 'Strict' or 'None'
    app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token_cookie'
    app.config['JWT_REFRESH_COOKIE_NAME'] = 'refresh_token_cookie'
    app.config['JWT_CSRF_IN_COOKIES'] = True # Store CSRF tokens in cookies
    app.config['JWT_COOKIE_DOMAIN'] = None  # None = same domain as server
    app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
    app.config['JWT_REFRESH_COOKIE_PATH'] = '/'

    # Initialize SQLAlchemy and Migrate with the app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize JWT with the app
    jwt.init_app(app)

    # Register modules
    module_manager = ModuleManager(app)
    module_manager.register_modules()

    # Initialize Flask-Mail (simulado cambiar luego)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = 'astronomiahub@gmail.com'
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_DEFAULT_SENDER'] = 'astronomiahub@gmail.com'
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
        from app.modules.token.models import Token
        
        jti = jwt_payload.get("jti")
        token = Token.query.filter_by(jti=jti).first()
        return not token or not token.is_active
    
    return app

def send_password_recovery_email(to_email, reset_link):
    msg = Message(
            subject="Password Reset Request",
            sender="noreply@astronomiahub.com",
            recipients=[to_email],
            body=f"Hello, \n\n"
                    f"We received a request to reset your password for your AstronomiaHub account.\n\n"
                    f"If you made this request, please click the link bellow to reset your password: {reset_link}\n\n"
                    f"If you did not request a password reset, you can safely ignore this email.\n\n"
                    f"Best regards,\n"
                    f"AstronomiaHub Team"
        )
    mail.send(msg)


app = create_app()