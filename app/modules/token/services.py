from app.modules.token.repositories import TokenRepository
from core.services.BaseService import BaseService


class TokenService(BaseService):
    def __init__(self):
        super().__init__(TokenRepository())
