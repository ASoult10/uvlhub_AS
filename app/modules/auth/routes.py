from flask import current_app, jsonify, redirect, render_template, request, url_for, flash, g, session
from flask_jwt_extended import get_jwt, jwt_required, unset_jwt_cookies
from flask_login import current_user, login_user, logout_user
import pyotp
from datetime import datetime, timezone
from werkzeug.exceptions import TooManyRequests

from app import db, limiter
from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, SignupForm, TwoFactorForm,RecoverPasswordForm,ResetPasswordForm
from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService
from app.modules.auth.models import User
from app.modules.token.services import TokenService

authentication_service = AuthenticationService()
user_profile_service = UserProfileService()
token_service = TokenService()

@auth_bp.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    # Resetea el contador de intentos de login al visitar la página de registro
    session.pop('login_attempts', None)

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
        response = authentication_service.login(
            email,
            form.password.data,
            remember=True,
            redirect_url=url_for("public.index")
        )
        return response

    return render_template("auth/signup_form.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    # Inicializa el contador en la sesión si no existe
    if 'login_attempts' not in session:
        session['login_attempts'] = 4

    remaining_attempts = session.get('login_attempts', 4)
    
    form = LoginForm()
    error_message = None

    if request.method == "POST":
        # Si ya no quedan intentos, lanza la excepción que activa el error 429
        if remaining_attempts <= 0:
            raise TooManyRequests()

        # Decrementa el contador en la sesión con cada intento POST
        session['login_attempts'] = remaining_attempts - 1
        
        if form.validate_on_submit():
            user = authentication_service.repository.get_by_email(form.email.data)

            if user and user.check_password(form.password.data):
                # Si el login es exitoso, resetea el contador
                session.pop('login_attempts', None)

                if user.has2FA:
                    redirect_url = url_for("auth.login_with_two_factor")
                else:
                    redirect_url = url_for("public.index")
                
                response = authentication_service.login(
                    form.email.data,
                    form.password.data,
                    form.remember_me.data,
                    redirect_url=redirect_url
                )
                
                if response:
                    return response
            
            error_message = "Invalid credentials"
        else:
            error_message = "Invalid form submission"

    # Obtiene el valor actualizado para pasarlo a la plantilla
    remaining_attempts = session.get('login_attempts', 3)
    return render_template(
        "auth/login_form.html", 
        form=form, 
        error=error_message, 
        remaining_attempts=remaining_attempts
    )

#Redirects to the 2fa login form
@auth_bp.route("/login/2fa-step", methods=["GET", "POST"])
def login_with_two_factor():
    
    form = TwoFactorForm()
    if request.method == "POST" and form.validate_on_submit():
        if authentication_service.check_temp_code(form.code.data):
            flash('Two-factor authentication worked', 'success')
            return redirect(url_for("public.index"))
        return render_template("auth/two_factor_login.html", form=form, error="Invalid 2FA code")
    return render_template("auth/two_factor_login.html", form=form)

#Checks the code for the 2fa login
@auth_bp.route("/login/2fa-step/verify", methods=["POST"])
def verify_2fa_login():
    code = request.form.get("code").strip()
    current_app.logger.debug("verify_2fa code=%r", code)

    if authentication_service.check_temp_code(code):
        # Update user's 2FA status
        current_user.has2FA = True
        db.session.add(current_user)
        db.session.commit()
        
        # Success flash message
        flash('Login with 2FA success', 'success')
        return redirect(url_for("public.index"))
    else:
        # Error flash message
        flash('Invalid verification code. Please try again.', 'error')
        return redirect(url_for("auth.login_with_two_factor"))

@auth_bp.route("/2fa-setup", methods=["GET"])
def two_factor_setup():
    if current_user.is_authenticated == False:
        return redirect(url_for("public.index"))
    
    form = TwoFactorForm()

    user = current_user
    if not user.user_secret or user.user_secret == '':
        secret = pyotp.random_base32()  
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
        current_user.has2FA = True
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
@jwt_required(optional=True)
def logout():
    response = redirect(url_for("public.index"))

    try:
        jwt_data = get_jwt()
        if jwt_data and "jti" in jwt_data:
            jti = jwt_data["jti"]
            access_token, refresh_token = token_service.get_pair_of_tokens_by_jti(jti)
            
            if access_token:
                token_service.revoke_token(access_token.id, current_user.id)
            
            if refresh_token:
                token_service.revoke_token(refresh_token.id, current_user.id)
                
    except Exception:
        pass

    unset_jwt_cookies(response)
    logout_user()
    return response

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
            AuthenticationService.send_password_recovery_email(email, reset_link)
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

