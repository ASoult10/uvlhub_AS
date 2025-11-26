from sqlalchemy import func

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DataSet
from app.modules.hubfile.models import Hubfile, HubfileDownloadRecord, HubfileViewRecord
from core.repositories.BaseRepository import BaseRepository


class HubfileRepository(BaseRepository):
    def __init__(self):
        super().__init__(Hubfile)

    def get(self, id):
        return db.session.get(self.model, id)

    def get_owner_user_by_hubfile(self, hubfile: Hubfile) -> User:
        # Find the User that owns the DataSet that the hubfile belongs to
        return (
            db.session.query(User)
            .join(DataSet, User.id == DataSet.user_id)
            .join(Hubfile, DataSet.id == Hubfile.dataset_id)
            .filter(Hubfile.id == hubfile.id)
            .first()
        )

    def get_dataset_by_hubfile(self, hubfile: Hubfile) -> DataSet:
        return db.session.query(DataSet).filter(DataSet.id == hubfile.dataset_id).first()

    # Nuevos métodos para el carrito
    def is_saved_by_user(self, hubfile_id: int, user_id: int) -> bool:
        hubfile = self.get(hubfile_id)
        if hubfile is None:
            return False
        return any(user.id == user_id for user in hubfile.saved_by_users)

    def add_to_user_saved(self, hubfile_id: int, user_id: int):
        hubfile = self.get(hubfile_id)
        user = db.session.get(User, user_id)
        if hubfile and user and not self.is_saved_by_user(hubfile_id, user_id):
            hubfile.saved_by_users.append(user)
            db.session.commit()

    def remove_from_user_saved(self, hubfile_id: int, user_id: int):
        hubfile = self.get(hubfile_id)
        user = db.session.get(User, user_id)
        if hubfile and user and self.is_saved_by_user(hubfile_id, user_id):
            hubfile.saved_by_users.remove(user)
            db.session.commit()

    def get_saved_files_for_user(self, user_id: int):
        user = db.session.get(User, user_id)
        if user:
            return user.saved_files.all()
        return []


class HubfileViewRecordRepository(BaseRepository):
    def __init__(self):
        super().__init__(HubfileViewRecord)

    def total_hubfile_views(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0


class HubfileDownloadRecordRepository(BaseRepository):
    def __init__(self):
        super().__init__(HubfileDownloadRecord)

    def total_hubfile_downloads(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0
