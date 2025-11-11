from datetime import datetime, timezone

from flask_login import UserMixin
import pyotp, qrcode
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    user_secret = db.Column(db.String(256), nullable = True, default = pyotp.random_base32()) #Secret for 2FA
    has2FA = db.Column(db.Boolean, nullable=False, default=False) #Indicates if 2FA is enabled
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    data_sets = db.relationship("DataSet", backref="user", lazy=True)
    profile = db.relationship("UserProfile", backref="user", uselist=False)

    # Relación: archivos guardados por este usuario
    saved_files = db.relationship(
        "Hubfile", secondary="user_saved_files", back_populates="saved_by_users", lazy="dynamic"
    )

    # Relación: tokens asociados a este usuario
    tokens = db.relationship(
        "Token",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if "password" in kwargs:
            self.set_password(kwargs["password"])
        if "user_secret" in kwargs:
            self.set_user_secret(kwargs["user_secret"])

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def set_user_secret(self, secret):
        self.user_secret = secret

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def temp_folder(self) -> str:
        from app.modules.auth.services import AuthenticationService

        return AuthenticationService().temp_folder_by_user(self)
