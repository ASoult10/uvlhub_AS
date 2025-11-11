from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index
from sqlalchemy.sql import func

from app import db


class CommentStatus(str, Enum):
    PENDING = "pending"
    VISIBLE = "visible"
    HIDDEN = "hidden"


class DSComment(db.Model):
    __tablename__ = "ds_comment"
    __mapper_args__ = {"eager_defaults": True}

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(
        db.Integer,
        db.ForeignKey("data_set.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )

    content = db.Column(db.Text, nullable=False)
    status = db.Column(
        SAEnum(
            CommentStatus,
            name="commentstatus",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=CommentStatus.VISIBLE,
        server_default=CommentStatus.VISIBLE.value,
    )
    created_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=func.now(),
    )

    # Backrefs
    data_set = db.relationship(
        "DataSet",
        backref=db.backref("comments", cascade="all, delete-orphan", lazy="dynamic"),
    )
    author = db.relationship(
        "User",
        backref=db.backref("dataset_comments", cascade="all, delete-orphan"),
    )

    __table_args__ = (
        Index("ix_ds_comment_dataset_id_created_at", "dataset_id", "created_at"),
    )

    @staticmethod
    def _to_epoch(dt):
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    def to_dict(self):
        status_str = (
            self.status.value if isinstance(self.status, CommentStatus) else str(self.status)
        )
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "author_id": self.author_id,
            "content": self.content,
            "status": status_str,
            "created_at": self._to_epoch(self.created_at),
            "updated_at": self._to_epoch(self.updated_at),
        }

    def __repr__(self) -> str:
        st = self.status.value if isinstance(self.status, CommentStatus) else self.status
        return f"<DSComment id={self.id} ds={self.dataset_id} author={self.author_id} status={st}>"
