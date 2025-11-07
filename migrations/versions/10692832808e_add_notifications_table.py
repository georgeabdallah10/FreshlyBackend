"""add notifications table

Revision ID: 10692832808e
Revises: cc165de93a4b
Create Date: 2025-11-06 05:02:55.774260
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '10692832808e'
down_revision: Union[str, Sequence[str], None] = 'cc165de93a4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create notifications table."""
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('related_meal_id', sa.Integer, sa.ForeignKey('meals.id', ondelete='SET NULL'), nullable=True),
        sa.Column('related_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('related_family_id', sa.Integer, sa.ForeignKey('families.id', ondelete='SET NULL'), nullable=True),
        #sa.Column('related_share_request_id', sa.Integer, sa.ForeignKey('meal_share_requests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_read', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create helpful indexes
    op.create_index(
        'ix_notifications_user_unread',
        'notifications',
        ['user_id'],
        postgresql_where=sa.text('is_read = false')
    )
    op.create_index(
        'ix_notifications_created_at',
        'notifications',
        ['created_at']
    )


def downgrade() -> None:
    """Downgrade schema: drop notifications table and indexes safely."""
    conn = op.get_bind()

    # Drop indexes if they exist
    for index_name in ['ix_notifications_created_at', 'ix_notifications_user_unread']:
        try:
            conn.execute(sa.text(f'DROP INDEX IF EXISTS {index_name}'))
        except Exception as e:
            print(f"⚠️ Skipping missing index {index_name}: {e}")

    # Drop the table if it exists
    try:
        conn.execute(sa.text('DROP TABLE IF EXISTS notifications CASCADE'))
    except Exception as e:
        print(f"⚠️ Skipping drop table notifications: {e}")