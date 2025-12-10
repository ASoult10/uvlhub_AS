import base64
import os
from io import BytesIO

import pyotp
import qrcode
from flask import redirect, request
from flask_jwt_extended import set_access_cookies, set_refresh_cookies
from flask_login import current_user, login_user
from flask_mail import Message

from app import mail
from app.modules.auth.models import User
from app.modules.auth.repositories import UserRepository
from app.modules.profile.models import UserProfile
from app.modules.profile.repositories import UserProfileRepository
from app.modules.token.services import service as TokenService
from core.configuration.configuration import uploads_folder_name
from core.services.BaseService import BaseService


class AuthenticationService(BaseService):
    def __init__(self):
        super().__init__(UserRepository())
        self.user_profile_repository = UserProfileRepository()

    def login(self, email, password, remember=True, redirect_url="public.index"):
        user = self.repository.get_by_email(email)
        if user is not None and user.check_password(password):
            login_user(user, remember=remember)
            user_id = int(user.id)
            device_info = TokenService.get_device_name_by_request(request) if request else None
            location_info = TokenService.get_location_by_ip(request.remote_addr) if request else None

            access_token, refresh_token = TokenService.create_tokens(user_id, device_info, location_info)

            response = redirect(redirect_url)
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response

        return False

    def is_email_available(self, email: str) -> bool:
        return self.repository.get_by_email(email) is None

    def create_with_profile(self, **kwargs):
        try:
            email = kwargs.pop("email", None)
            password = kwargs.pop("password", None)
            name = kwargs.pop("name", None)
            surname = kwargs.pop("surname", None)

            if not email:
                raise ValueError("Email is required.")
            if not password:
                raise ValueError("Password is required.")
            if not name:
                raise ValueError("Name is required.")
            if not surname:
                raise ValueError("Surname is required.")

            user_data = {"email": email, "password": password}

            profile_data = {
                "name": name,
                "surname": surname,
            }

            user = self.create(commit=False, **user_data)
            profile_data["user_id"] = user.id
            self.user_profile_repository.create(**profile_data)
            self.repository.session.commit()
        except Exception as exc:
            self.repository.session.rollback()
            raise exc
        return user

    def update_profile(self, user_profile_id, form):
        if form.validate():
            updated_instance = self.update(user_profile_id, **form.data)
            return updated_instance, None

        return None, form.errors

    def get_authenticated_user(self) -> User | None:
        if current_user.is_authenticated:
            return current_user
        return None

    def get_authenticated_user_profile(self) -> UserProfile | None:
        if current_user.is_authenticated:
            return current_user.profile
        return None

    def check_temp_code(self, code: str) -> bool:
        user = current_user
        if not user or not user.user_secret:
            return False

        totp = pyotp.TOTP(user.user_secret).now()
        return code == totp

    def generate_qr_code_uri(self, uri: str):
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        tempImg = BytesIO()
        img.save(tempImg, format="PNG")
        qr_b64 = base64.b64encode(tempImg.getvalue()).decode("utf-8")
        return qr_b64

    def temp_folder_by_user(self, user: User) -> str:
        return os.path.join(uploads_folder_name(), "temp", str(user.id))

    def send_password_recovery_email(self, to_email, reset_link):
        msg = Message(
            subject="Password Reset Request",
            sender="noreply@astronomiahub.com",
            recipients=[to_email],
            body=(
                "Hello,\n\n"
                "We received a request to reset your password for your AstronomiaHub account.\n\n"
                f"If you made this request, please click the link below to reset your password:\n{reset_link}\n\n"
                "If you did not request a password reset, you can safely ignore this email.\n\n"
                "Best regards,\n"
                "AstronomiaHub Team"
            ),
        )
        mail.send(msg)


