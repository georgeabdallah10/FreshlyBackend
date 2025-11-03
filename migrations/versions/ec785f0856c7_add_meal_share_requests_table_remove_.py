"""add_meal_share_requests_table_remove_shared_with_family

Revision ID: ec785f0856c7
Revises: 2b48126c9550
Create Date: 2025-11-02 19:28:09.952095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec785f0856c7'
down_revision: Union[str, Sequence[str], None] = '2b48126c9550'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum for meal share request status
    op.execute("CREATE TYPE meal_share_request_status AS ENUM ('pending', 'accepted', 'declined')")
    
    # Create meal_share_requests table
    op.create_table(
        'meal_share_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meal_id', sa.Integer(), nullable=False),
        sa.Column('sender_user_id', sa.Integer(), nullable=False),
        sa.Column('recipient_user_id', sa.Integer(), nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'accepted', 'declined', name='meal_share_request_status'), nullable=False, server_default='pending'),
        sa.Column('message', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['meal_id'], ['meals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_meal_share_requests_recipient_user_id', 'meal_share_requests', ['recipient_user_id'])
    op.create_index('ix_meal_share_requests_sender_user_id', 'meal_share_requests', ['sender_user_id'])
    op.create_index('ix_meal_share_requests_status', 'meal_share_requests', ['status'])
    
    # Remove shared_with_family column from meals table (if it exists)
    op.execute("ALTER TABLE meals DROP COLUMN IF EXISTS shared_with_family")


def downgrade() -> None:
    """Downgrade schema."""
    # Add back shared_with_family column
    op.add_column('meals', sa.Column('shared_with_family', sa.Boolean(), nullable=False, server_default='false'))
    
    # Drop indexes
    op.drop_index('ix_meal_share_requests_status', table_name='meal_share_requests')
    op.drop_index('ix_meal_share_requests_sender_user_id', table_name='meal_share_requests')
    op.drop_index('ix_meal_share_requests_recipient_user_id', table_name='meal_share_requests')
    
    # Drop table
    op.drop_table('meal_share_requests')
    
    # Drop enum
    op.execute("DROP TYPE meal_share_request_status")
