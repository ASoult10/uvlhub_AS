import os
from typing import List, Optional, Tuple

from app.modules.auth.models import User
from app.modules.dataset.models import DataSet
from app.modules.dataset.models_comments import DSComment, CommentStatus
from app.modules.dataset.repositories import DataSetRepository
from app.modules.dataset.repositories_comments import DSCommentRepository
from core.services.BaseService import BaseService


class DSCommentService(BaseService):
    def __init__(self):
        super().__init__(DSCommentRepository())
        self.dataset_repository = DataSetRepository()

    def _is_admin(self, user: User) -> bool:
        if hasattr(user, "is_admin"):
            try:
                return bool(getattr(user, "is_admin"))
            except Exception:
                pass
        admin_emails = (os.getenv("ADMIN_EMAILS", "") or "")
        admin_list = [e.strip().lower() for e in admin_emails.split(",") if e.strip()]
        return bool(user and user.email.lower() in admin_list)

    def _can_moderate(self, user: User, dataset: DataSet) -> bool:
        if not user or not dataset:
            return False
        return self._is_admin(user) or (dataset.user_id == user.id)

    def add_comment(self, dataset_id: int, author_id: int, content: str) -> Tuple[Optional[DSComment], Optional[str]]:
        dataset = self.dataset_repository.get_by_id(dataset_id)
        if not dataset:
            return None, "Dataset not found"

        content = (content or "").strip()
        if not content:
            return None, "Content cannot be empty"

        comment = self.repository.create(
            dataset_id=dataset_id,
            author_id=author_id,
            content=content,
            status=CommentStatus.VISIBLE,
        )
        return comment, None

    def list_visible(self, dataset_id: int) -> List[DSComment]:
        return self.repository.list_for_dataset(
            dataset_id, include_hidden=False, include_pending=False, newest_first=True
        )

    def list_all_for_moderation(self, dataset_id: int, requester: User) -> Tuple[Optional[List[DSComment]], Optional[str]]:
        dataset = self.dataset_repository.get_by_id(dataset_id)
        if not dataset:
            return None, "Dataset not found"
        if not self._can_moderate(requester, dataset):
            return None, "You do not have permission to moderate comments on this dataset."

        comments = self.repository.list_for_dataset(
            dataset_id, include_hidden=True, include_pending=True, newest_first=True
        )
        return comments, None

    def moderate(self, dataset_id: int, comment_id: int, action: str, requester: User) -> Tuple[bool, Optional[str]]:
        dataset = self.dataset_repository.get_by_id(dataset_id)
        if not dataset:
            return False, "Dataset not found"

        if not self._can_moderate(requester, dataset):
            return False, "You do not have permission to moderate comments on this dataset."

        comment = self.repository.get_for_dataset(dataset_id, comment_id)
        if not comment:
            return False, "Comment not found"

        action = (action or "").lower().strip()
        if action == "hide":
            self.repository.set_status(comment, CommentStatus.HIDDEN)
            return True, None
        elif action == "show":
            self.repository.set_status(comment, CommentStatus.VISIBLE)
            return True, None
        elif action in ("delete", "remove"):
            self.repository.delete(comment.id)
            return True, None
        else:
            return False, "Unknown action. Use 'hide', 'show', or 'delete'."
