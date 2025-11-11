"""empty message

Revision ID: 5bc57677d35f
Revises: 002_add_ds_comment, 3b04e6420808, 73bf25f2eee6
Create Date: 2025-11-11 13:42:23.758542

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bc57677d35f'
down_revision = ('002_add_ds_comment', '3b04e6420808', '73bf25f2eee6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
