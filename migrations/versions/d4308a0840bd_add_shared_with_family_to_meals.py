"""add_shared_with_family_to_meals

Revision ID: d4308a0840bd
Revises: 53525018d25f
Create Date: 2025-11-02 18:12:30.892908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4308a0840bd'
down_revision: Union[str, Sequence[str], None] = '53525018d25f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add shared_with_family column to meals table
    op.add_column('meals', sa.Column('shared_with_family', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove shared_with_family column from meals table
    op.drop_column('meals', 'shared_with_family')
