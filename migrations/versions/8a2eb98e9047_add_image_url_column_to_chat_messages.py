"""add image_url column to chat_messages

Revision ID: 8a2eb98e9047
Revises: 9732d1cad282
Create Date: 2025-12-20 15:25:24.966221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a2eb98e9047'
down_revision: Union[str, Sequence[str], None] = '9732d1cad282'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('chat_messages', sa.Column('image_url', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chat_messages', 'image_url')
