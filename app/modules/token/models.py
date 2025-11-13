from app import db
from enum import Enum as PyEnum
from sqlalchemy import Enum as SQLEnum


class TokenType(PyEnum):
    SESSION_TOKEN = "Session_Token"
    REFRESH_TOKEN = "Refresh_Token"


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(256), unique=False, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="tokens")
    type = db.Column(
        SQLEnum(TokenType, name="token_type", native_enum=False),
        nullable=False
    )
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    device_info = db.Column(db.String(256), nullable=False, default="Unknown Device")
    location_info = db.Column(db.String(256), nullable=False, default="Unknown Location")


    def __repr__(self):
        return f'Token<{self.id} for User {self.user_id}>'
    
    def __init__(self, **kwargs):
        super(Token, self).__init__(**kwargs)

    def is_expired(self, current_time):
        return current_time >= self.expires_at