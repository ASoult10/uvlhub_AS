import logging
from typing import List, Optional

from sqlalchemy import asc, desc

from app import db
from app.modules.dataset.models_comments import CommentStatus, DSComment
from core.repositories.BaseRepository import BaseRepository

logger = logging.getLogger(__name__)


class DSCommentRepository(BaseRepository[DSComment]):
    def __init__(self):
        super().__init__(DSComment)
        self.session = db.session

    def create(self, **kwargs) -> DSComment:
        """Create garantizando commit y refresh para tener defaults del servidor."""
        obj = DSComment(**kwargs)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def list_for_dataset(
        self,
        dataset_id: int,
        include_hidden: bool = False,
        include_pending: bool = False,
        newest_first: bool = True,
    ) -> List[DSComment]:
        q = self.model.query.filter_by(dataset_id=dataset_id)
        if not include_hidden:
            q = q.filter(self.model.status == CommentStatus.VISIBLE)
        if not include_pending:
            q = q.filter(self.model.status != CommentStatus.PENDING)
        q = q.order_by(desc(self.model.created_at) if newest_first else asc(self.model.created_at))
        return q.all()

    def get_for_dataset(self, dataset_id: int, comment_id: int) -> Optional[DSComment]:
        return self.model.query.filter_by(dataset_id=dataset_id, id=comment_id).first()

    def set_status(self, comment: DSComment, status: CommentStatus) -> DSComment:
        comment.status = status
        self.session.add(comment)
        self.session.commit()
        self.session.refresh(comment)
        return comment

    def delete(self, id: int) -> bool:
        comment = self.get_by_id(id)
        if not comment:
            return False
        self.session.delete(comment)
        self.session.commit()
        return True
