"""Change unit_id to unit string

Revision ID: f2580d3a8763
Revises: 663a559a6821
Create Date: 2025-10-20 00:07:14.908840
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f2580d3a8763'
down_revision: Union[str, Sequence[str], None] = '663a559a6821'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- 1. Pantry item change ---
    op.drop_constraint(op.f('pantry_items_unit_id_fkey'), 'pantry_items', type_='foreignkey')
    op.drop_column('pantry_items', 'unit_id')
    op.add_column('pantry_items', sa.Column('unit', sa.String(length=64), nullable=True))

    # --- 2. Fix user status safely ---
    # Backfill NULL statuses before setting NOT NULL
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")

    op.alter_column(
        'users',
        'status',
        existing_type=sa.VARCHAR(length=50),
        nullable=False,
        server_default=sa.text("'active'")
    )

    # ⚠️ Do NOT drop updated_at (keep it in your DB)
    # The old autogen line was:
    # op.drop_column('users', 'updated_at')
    # — removed to prevent breaking your trigger or model.


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'users',
        'status',
        existing_type=sa.VARCHAR(length=50),
        nullable=True,
        server_default=sa.text("'active'")
    )

    op.drop_column('pantry_items', 'unit')
    op.add_column('pantry_items', sa.Column('unit_id', sa.INTEGER(), nullable=True))
    op.create_foreign_key(op.f('pantry_items_unit_id_fkey'), 'pantry_items', 'units', ['unit_id'], ['id'])