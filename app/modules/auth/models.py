from datetime import datetime, timezone, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

from app import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    data_sets = db.relationship("DataSet", backref="user", lazy=True)
    profile = db.relationship("UserProfile", backref="user", uselist=False)
    reset_token = db.Column(db.String(256), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if "password" in kwargs:
            self.set_password(kwargs["password"])

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def temp_folder(self) -> str:
        from app.modules.auth.services import AuthenticationService

        return AuthenticationService().temp_folder_by_user(self)

    def generate_reset_token(self) -> str:
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = serializer.dumps({'user_id': self.id})
        self.reset_token = token
        self.reset_token_expiration = datetime.now() + timedelta(minutes=30)
        db.session.commit()
        return token
    
    @staticmethod
    def verify_reset_token(token: str, expiration: int = 1800):
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = serializer.loads(token, max_age=expiration)
            user_id = data.get('user_id')
        except Exception:
            return None
        return User.query.get(user_id)