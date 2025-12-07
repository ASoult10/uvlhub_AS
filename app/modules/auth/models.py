from datetime import datetime, timedelta, timezone

import pyotp
from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

# Tabla asociativa many-to-many entre usuarios y roles
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Role {self.name}>"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    user_secret = db.Column(db.String(256), nullable=True, default=pyotp.random_base32())  # Secret for 2FA
    has2FA = db.Column(db.Boolean, nullable=False, default=False)  # Indicates if 2FA is enabled
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    data_sets = db.relationship("DataSet", backref="user", lazy=True)
    profile = db.relationship("UserProfile", backref="user", uselist=False)
    reset_token = db.Column(db.String(256), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    # Relación: archivos guardados por este usuario
    saved_files = db.relationship(
        "Hubfile", secondary="user_saved_files", back_populates="saved_by_users", lazy="dynamic"
    )

    # Relación: tokens asociados a este usuario
    tokens = db.relationship("Token", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    # Relación: roles del usuario
    roles = db.relationship("Role", secondary="user_roles", backref=db.backref("users", lazy="dynamic"), lazy="dynamic")

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

    def generate_reset_token(self) -> str:
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = serializer.dumps({"user_id": self.id})
        self.reset_token = token
        self.reset_token_expiration = datetime.now() + timedelta(minutes=30)
        db.session.commit()
        return token

    @staticmethod
    def verify_reset_token(token: str, expiration: int = 1800):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = serializer.loads(token, max_age=expiration)
            user_id = data.get("user_id")
        except Exception:
            return None
        return User.query.get(user_id)

    def has_role(self, role_name: str) -> bool:
        return self.roles.filter_by(name=role_name).count() > 0

    def add_role(self, role):
        if isinstance(role, str):
            from app.modules.auth.roles import Role as RoleModel

            role_obj = RoleModel.query.filter_by(name=role).first()
        else:
            role_obj = role
        if role_obj and not self.has_role(role_obj.name):
            self.roles.append(role_obj)

    def remove_role(self, role):
        if isinstance(role, str):
            from app.modules.auth.roles import Role as RoleModel

            role_obj = RoleModel.query.filter_by(name=role).first()
        else:
            role_obj = role
        if role_obj and self.has_role(role_obj.name):
            self.roles.remove(role_obj)
