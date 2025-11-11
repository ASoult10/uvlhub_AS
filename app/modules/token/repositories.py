from app.modules.token.models import Token
from core.repositories.BaseRepository import BaseRepository


class TokenRepository(BaseRepository):
    def __init__(self):
        super().__init__(Token)
