from flask import redirect, render_template, request, url_for, flash
from flask_login import current_user, login_user, logout_user
from datetime import datetime, timezone

from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, SignupForm, RecoverPasswordForm, ResetPasswordForm
from app.modules.auth.services import AuthenticationService, send_password_recovery_email
from app.modules.profile.services import UserProfileService
from app import db
from app.modules.auth.models import User

authentication_service = AuthenticationService()
user_profile_service = UserProfileService()


@auth_bp.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        if not authentication_service.is_email_available(email):
            return render_template("auth/signup_form.html", form=form, error=f"Email {email} in use")

        try:
            user = authentication_service.create_with_profile(**form.data)
        except Exception as exc:
            return render_template("auth/signup_form.html", form=form, error=f"Error creating user: {exc}")

        # Log user
        login_user(user, remember=True)
        return redirect(url_for("public.index"))

    return render_template("auth/signup_form.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        if authentication_service.login(form.email.data, form.password.data):
            return redirect(url_for("public.index"))

        return render_template("auth/login_form.html", form=form, error="Invalid credentials")

    return render_template("auth/login_form.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.index"))


@auth_bp.route("/recover-password/", methods=["GET", "POST"])
def recover_password():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = RecoverPasswordForm()
    if form.validate_on_submit():
        email = request.form.get("email")
        user = authentication_service.repository.get_by_email(email)

        if not user:
            flash("The email address is not registered in our system.", "error")
            return redirect(url_for("auth.recover_password"))

        if user:
            token = user.generate_reset_token()
            reset_link = url_for("auth.reset_password", token=token, _external=True)
            send_password_recovery_email(email, reset_link)
            flash("A password recovery email has been sent.", "info")
        
        return redirect(url_for("auth.recover_password"))

    return render_template("auth/recover_password_form.html", form=form)

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    user = User.verify_reset_token(token)
    if not user or user.reset_token_expiration < datetime.now():
        flash("The password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.recover_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expiration = None
        db.session.commit()
        flash("Your password has been reset successfully.", "success")
        return redirect(url_for("auth.recover_password"))

    return render_template("auth/reset_password_form.html", form=form)

