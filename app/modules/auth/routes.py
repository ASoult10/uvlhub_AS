from flask import current_app, redirect, render_template, request, url_for, flash
from flask_login import current_user, login_user, logout_user
import pyotp
from app.modules.auth import auth_bp
from app import db
from app.modules.auth.forms import LoginForm, SignupForm, TwoFactorForm
from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService

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

@auth_bp.route("/2fa-setup", methods=["GET"])
def two_factor_setup():
    if current_user.is_authenticated == False:
        return redirect(url_for("public.index"))
    
    form = TwoFactorForm()

    user = current_user
    if not user.user_secret or user.user_secret == '':
        secret = pyotp.random_base32()  # e.g., 16 chars
        user.set_user_secret(secret)
        db.session.add(user)
        db.session.commit()
    else:
        secret = user.user_secret

    #uri with encoded information of the user and the provider
    issuer = "ASTRONOMÍAHUB"
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
    qr_b64 = authentication_service.generate_qr_code_uri(uri)
    form = TwoFactorForm()
    
    return render_template("auth/two_factor_setup.html", qr_b64 = qr_b64, form = form)

@auth_bp.route("/2fa-setup/verify", methods=["POST"])
def verify_2fa():
    code = request.form.get("code").strip()
    current_app.logger.debug("verify_2fa code=%r", code)

    if authentication_service.check_temp_code(code):
        # Update user's 2FA status
        current_user.two_factor_enabled = True
        db.session.add(current_user)
        db.session.commit()
        
        # Success flash message
        flash('Two-factor authentication has been successfully enabled for your account!', 'success')
        return redirect(url_for("public.index"))
    else:
        # Error flash message
        flash('Invalid verification code. Please try again.', 'error')
        return redirect(url_for("auth.two_factor_setup"))


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.index"))
