"""add category to pantry_items

Revision ID: 6bc299328adb
Revises: eb5a72a60a86
Create Date: 2025-10-13 10:01:37.336535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bc299328adb'
down_revision: Union[str, Sequence[str], None] = 'eb5a72a60a86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pantry_items', sa.Column('category', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    pass
