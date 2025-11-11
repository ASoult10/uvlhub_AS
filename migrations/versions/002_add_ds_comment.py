"""add ds_comment table

Revision ID: 002_add_ds_comment
Revises: 001
Create Date: 2025-11-05
"""
import sqlalchemy as sa
from alembic import op

revision = "002_add_ds_comment"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    comment_status = sa.Enum("pending", "visible", "hidden", name="commentstatus")
    if bind.dialect.name == "postgresql":
        comment_status.create(bind, checkfirst=True)

    op.create_table(
        "ds_comment",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("data_set.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),

        sa.Column("content", sa.Text(), nullable=False),

        sa.Column("status", comment_status, nullable=False, server_default="visible"),
    
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_index(
        "ix_ds_comment_dataset_id_created_at",
        "ds_comment",
        ["dataset_id", "created_at"],
    )


def downgrade():
    bind = op.get_bind()

    op.drop_index("ix_ds_comment_dataset_id_created_at", table_name="ds_comment")
    op.drop_table("ds_comment")

    comment_status = sa.Enum("pending", "visible", "hidden", name="commentstatus")
    if bind.dialect.name == "postgresql":
        comment_status.drop(bind, checkfirst=True)
