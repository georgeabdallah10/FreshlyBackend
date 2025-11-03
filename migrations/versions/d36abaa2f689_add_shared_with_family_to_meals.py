"""add_shared_with_family_to_meals

Revision ID: d36abaa2f689
Revises: d4308a0840bd
Create Date: 2025-11-02 19:01:29.695152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd36abaa2f689'
down_revision: Union[str, Sequence[str], None] = 'd4308a0840bd'
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
