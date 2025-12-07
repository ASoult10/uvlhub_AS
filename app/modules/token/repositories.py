from app.modules.token.models import Token
from core.repositories.BaseRepository import BaseRepository


class TokenRepository(BaseRepository):

    def __init__(self):
        super().__init__(Token)

    def get_token_by_id(self, token_id: int):
        return self.model.query.filter_by(id=token_id).first()

    def get_token_by_jti(self, jti: str):
        return self.model.query.filter_by(jti=jti).first()

    def get_active_access_token_by_parent_jti(self, parent_jti):
        return self.model.query.filter_by(parent_jti=parent_jti, type="access_token", is_active=True).first()

    def get_active_tokens_by_user(self, user_id: int):
        return self.model.query.filter_by(user_id=user_id, is_active=True).all()

    def get_all_tokens_by_user(self, user_id: int):
        return self.model.query.filter_by(user_id=user_id).all()

    def save_token(self, token: Token):
        merged = self.session.merge(token)
        self.session.commit()
        return merged

    def delete_token(self, token: Token):
        self.session.delete(token)
        self.session.commit()
