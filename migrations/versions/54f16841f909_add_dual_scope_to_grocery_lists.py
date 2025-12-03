"""add_dual_scope_to_grocery_lists

Revision ID: 54f16841f909
Revises: 1f5f699c2f99
Create Date: 2025-12-03 12:35:56.446906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54f16841f909'
down_revision: Union[str, Sequence[str], None] = '1f5f699c2f99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dual-scope support to grocery_lists table."""
    # Add owner_user_id column (nullable initially for existing data)
    op.add_column('grocery_lists',
        sa.Column('owner_user_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_grocery_lists_owner_user_id',
        'grocery_lists', 'users',
        ['owner_user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Make family_id nullable (was required before)
    op.alter_column('grocery_lists', 'family_id',
                   existing_type=sa.Integer(),
                   nullable=True)

    # Add XOR constraint (exactly one must be set)
    op.create_check_constraint(
        'grocery_list_scope_xor',
        'grocery_lists',
        '(family_id IS NOT NULL AND owner_user_id IS NULL) OR '
        '(family_id IS NULL AND owner_user_id IS NOT NULL)'
    )

    # Add composite indexes for common query patterns
    op.create_index(
        'idx_grocery_list_family_status',
        'grocery_lists',
        ['family_id', 'status']
    )
    op.create_index(
        'idx_grocery_list_owner_status',
        'grocery_lists',
        ['owner_user_id', 'status']
    )

    # Add index for meal_plan_id lookups
    op.create_index(
        'idx_grocery_list_meal_plan',
        'grocery_lists',
        ['meal_plan_id']
    )


def downgrade() -> None:
    """Remove dual-scope support from grocery_lists table."""
    op.drop_index('idx_grocery_list_meal_plan', table_name='grocery_lists')
    op.drop_index('idx_grocery_list_owner_status', table_name='grocery_lists')
    op.drop_index('idx_grocery_list_family_status', table_name='grocery_lists')
    op.drop_constraint('grocery_list_scope_xor', 'grocery_lists', type_='check')
    op.alter_column('grocery_lists', 'family_id',
                   existing_type=sa.Integer(),
                   nullable=False)
    op.drop_constraint('fk_grocery_lists_owner_user_id', 'grocery_lists', type_='foreignkey')
    op.drop_column('grocery_lists', 'owner_user_id')
