from app.modules.fakenodo.repositories import FakenodoRepository
from core.services.BaseService import BaseService

from app.modules.dataset.models import DataSet
import secrets


class FakenodoService(BaseService):
    def __init__(self):
        super().__init__(FakenodoRepository())


    def create_new_deposition(self, dataset: DataSet) -> dict:
 
        random_numbers1 = ''.join([str(secrets.randbelow(10)) for _ in range(2)])
        random_numbers2 = ''.join([str(secrets.randbelow(10)) for _ in range(4)])
        fakenodo_doi = f"{random_numbers1}.{random_numbers2}/{dataset.ds_meta_data.title}"
        response = {
            "fakenodo_doi": fakenodo_doi,
            "status_code": 201
        }

        return response
   
