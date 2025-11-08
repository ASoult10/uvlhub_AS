from app.modules.explore.repositories import ExploreRepository
from core.services.BaseService import BaseService


class ExploreService(BaseService):
    def __init__(self):
        super().__init__(ExploreRepository())

    def filter(self, query="", date_after=None, date_before=None, author="any", sorting="newest",
               publication_type="any", tags=[], **kwargs):
        return self.repository.filter(query, date_after, date_before, author, sorting, publication_type, tags, **kwargs)
