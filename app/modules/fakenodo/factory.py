import os

from app.modules.fakenodo.services import FakenodoService
from app.modules.zenodo.services import ZenodoService


def get_zenodo_service():

    fakenodo_url = os.getenv("FAKENODO_URL")

    if fakenodo_url:
        return FakenodoService(base_url=fakenodo_url)

    return ZenodoService()
