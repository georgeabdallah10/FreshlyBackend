"""add phone_number to users

Revision ID: 303558a71cb8
Revises: a7b3a8b5cf0e
Create Date: 2025-10-05 15:46:59.298563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '303558a71cb8'
down_revision: Union[str, Sequence[str], None] = 'a7b3a8b5cf0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("phone_number", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "phone_number")