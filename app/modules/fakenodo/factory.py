import os

from app.modules.zenodo.services import ZenodoService
from app.modules.fakenodo.services import FakenodoService


def get_zenodo_service():
 
    fakenodo_url = os.getenv("FAKENODO_URL")

    if fakenodo_url:
        return FakenodoService(base_url=fakenodo_url)

    return ZenodoService()