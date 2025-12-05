from flask import render_template, flash
from app.modules.auth.forms import LoginForm


class ErrorHandlerManager:
    def __init__(self, app):
        self.app = app

    def register_error_handlers(self):
        @self.app.errorhandler(500)
        def internal_error(e):
            self.app.logger.error("Internal Server Error: %s", str(e))
            return render_template("500.html"), 500

        @self.app.errorhandler(404)
        def not_found_error(e):
            self.app.logger.warning("Page Not Found: %s", str(e))
            return render_template("404.html"), 404

        @self.app.errorhandler(401)
        def unauthorized_error(e):
            self.app.logger.warning("Unauthorized Access: %s", str(e))
            return render_template("401.html"), 401

        @self.app.errorhandler(400)
        def bad_request_error(e):
            self.app.logger.warning("Bad Request: %s", str(e))
            return render_template("400.html"), 400

        @self.app.errorhandler(429)
        def ratelimit_handler(e):
            self.app.logger.warning("Rate limit exceeded: %s", str(e))
            flash("You have exceeded the login attempt limit. Please try again later.", "error")
            form = LoginForm()
            return render_template("auth/login_form.html", form=form), 429
