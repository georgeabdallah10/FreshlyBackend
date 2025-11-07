"""add_shared_with_family_to_meals

Revision ID: 2b48126c9550
Revises: d36abaa2f689
Create Date: 2025-11-02 19:02:55.914670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b48126c9550'
down_revision: Union[str, Sequence[str], None] = '53525018d25f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('meals', sa.Column('shared_with_family', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('meals', 'shared_with_family')
