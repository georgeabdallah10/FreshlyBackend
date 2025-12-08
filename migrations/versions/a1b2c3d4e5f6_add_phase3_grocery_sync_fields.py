"""add_phase3_grocery_sync_fields

Add is_purchased, is_manual, and source_meal_plan_id fields to grocery_list_items
for Phase 3 smart syncing between pantry and grocery lists.

Revision ID: a1b2c3d4e5f6
Revises: 013a6556c321
Create Date: 2025-12-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '013a6556c321'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 3 grocery sync fields."""
    # Add is_purchased field
    op.add_column(
        'grocery_list_items',
        sa.Column(
            'is_purchased',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if the user already bought this item'
        )
    )

    # Add is_manual field
    op.add_column(
        'grocery_list_items',
        sa.Column(
            'is_manual',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if manually added by user (not generated from meal plan)'
        )
    )

    # Add source_meal_plan_id field with foreign key
    op.add_column(
        'grocery_list_items',
        sa.Column(
            'source_meal_plan_id',
            sa.Integer(),
            nullable=True,
            comment='Meal plan that generated this item (for rebuilds)'
        )
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_grocery_list_items_source_meal_plan',
        'grocery_list_items',
        'meal_plans',
        ['source_meal_plan_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index on source_meal_plan_id for faster lookups during rebuilds
    op.create_index(
        'idx_grocery_list_items_source_meal_plan',
        'grocery_list_items',
        ['source_meal_plan_id']
    )


def downgrade() -> None:
    """Remove Phase 3 grocery sync fields."""
    # Drop index
    op.drop_index('idx_grocery_list_items_source_meal_plan', table_name='grocery_list_items')

    # Drop foreign key constraint
    op.drop_constraint('fk_grocery_list_items_source_meal_plan', 'grocery_list_items', type_='foreignkey')

    # Drop columns
    op.drop_column('grocery_list_items', 'source_meal_plan_id')
    op.drop_column('grocery_list_items', 'is_manual')
    op.drop_column('grocery_list_items', 'is_purchased')
