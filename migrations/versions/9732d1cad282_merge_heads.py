"""merge heads

Revision ID: 9732d1cad282
Revises: 573d0f0f08cd, a3a9c24d6d4d
Create Date: 2025-12-19 09:25:57.873252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9732d1cad282'
down_revision: Union[str, Sequence[str], None] = ('573d0f0f08cd', 'a3a9c24d6d4d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
