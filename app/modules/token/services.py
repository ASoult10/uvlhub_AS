from app.modules.token.repositories import TokenRepository
from core.services.BaseService import BaseService
from app.modules.token.models import Token


class TokenService(BaseService):
    
    def __init__(self):
        super().__init__(TokenRepository())
        self.repository = self.get_repository()
    
    def get_token_by_id(self, token_id: int):
        return self.repository.get_token_by_id(token_id)

    def get_token_by_code(self, code: str):
        return self.repository.get_token_by_code(code)

    def get_active_tokens_by_user(self, user_id: int):
        return self.repository.get_active_tokens_by_user(user_id)

    def get_all_tokens_by_user(self, user_id: int):
        return self.repository.get_all_tokens_by_user(user_id)

    def revoke_token(self, token_id: int, user_id: int):
        token_to_revoke = self.get_token_by_id(token_id)
        if token_to_revoke.user_id == user_id:
            self.edit_token(token_id, is_active=False)
            return True
        return False

    def revoke_all_tokens_for_user(self, user_id: int) -> int:
        tokens_to_revoke = self.get_all_tokens_by_user(user_id)
        for token in tokens_to_revoke:
                self.edit_token(token.id, is_active=False)
        return len(tokens_to_revoke)
    
    def save_token(self, **kwargs):
        new_token = Token(**kwargs)
        return self.repository.save_token(new_token)
    
    def edit_token(self, token_id: int, **kwargs):
        token_to_edit = self.get_token_by_id(token_id)
        for key, value in kwargs.items():
            if key == 'id':
                continue
            setattr(token_to_edit, key, value)
        merged = self.repository.save_token(token_to_edit)
        return merged

    def delete_token(self, token_id: int):
        token_to_delete = self.get_token_by_id(token_id)
        self.repository.delete_token(token_to_delete)