"""add_updated_at_to_users

Revision ID: 53525018d25f
Revises: 506004e3d170
Create Date: 2025-11-01 13:29:34.047606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53525018d25f'
down_revision: Union[str, Sequence[str], None] = 'e7297cd4ed75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add updated_at column to users table
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                     server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove updated_at column from users table
    op.drop_column('users', 'updated_at')
