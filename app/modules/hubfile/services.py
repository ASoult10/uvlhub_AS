import os

from app.modules.auth.models import User
from app.modules.dataset.models import DataSet
from app.modules.hubfile.models import Hubfile
from app.modules.hubfile.repositories import (
    HubfileDownloadRecordRepository,
    HubfileRepository,
    HubfileViewRecordRepository,
)
from core.services.BaseService import BaseService


class HubfileService(BaseService):
    def __init__(self):
        super().__init__(HubfileRepository())
        self.hubfile_view_record_repository = HubfileViewRecordRepository()
        self.hubfile_download_record_repository = HubfileDownloadRecordRepository()

    def get_owner_user_by_hubfile(self, hubfile: Hubfile) -> User:
        return self.repository.get_owner_user_by_hubfile(hubfile)

    def get_dataset_by_hubfile(self, hubfile: Hubfile) -> DataSet:
        return self.repository.get_dataset_by_hubfile(hubfile)

    def get_path_by_hubfile(self, hubfile: Hubfile) -> str:
        hubfile_user = self.get_owner_user_by_hubfile(hubfile)
        hubfile_dataset = self.get_dataset_by_hubfile(hubfile)
        working_dir = os.getenv("WORKING_DIR")

        path = os.path.join(
            working_dir, "uploads", f"user_{hubfile_user.id}", f"dataset_{hubfile_dataset.id}", hubfile.name
        )
        return path

    def total_hubfile_views(self) -> int:
        return self.hubfile_view_record_repository.total_hubfile_views()

    def total_hubfile_downloads(self) -> int:
        return self.hubfile_download_record_repository.total_hubfile_downloads()

    # Nuevos métodos para el carrito de archivos
    def is_saved_by_user(self, hubfile_id: int, user_id: int) -> bool:
        return self.repository.is_saved_by_user(hubfile_id, user_id)

    def add_to_user_saved(self, hubfile_id: int, user_id: int):
        self.repository.add_to_user_saved(hubfile_id, user_id)

    def remove_from_user_saved(self, hubfile_id: int, user_id: int):
        self.repository.remove_from_user_saved(hubfile_id, user_id)

    def get_saved_files_for_user(self, user_id: int):
        return self.repository.get_saved_files_for_user(user_id)


class HubfileDownloadRecordService(BaseService):
    def __init__(self):
        super().__init__(HubfileDownloadRecordRepository())
