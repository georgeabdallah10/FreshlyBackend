"""personal pantry support

Revision ID: bc34e6bd7070
Revises: 303558a71cb8
Create Date: 2025-10-12 21:50:10.701922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc34e6bd7070'
down_revision: Union[str, Sequence[str], None] = '303558a71cb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pantry_items", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.create_index("ix_pantry_items_owner_user_id", "pantry_items", ["owner_user_id"])
    op.create_foreign_key(
        "fk_pantry_items_owner_user_id_users",
        "pantry_items", "users",
        ["owner_user_id"], ["id"],
        ondelete="CASCADE"
    )
    op.create_check_constraint(
        "pantry_scope_xor",
        "pantry_items",
        "(family_id IS NOT NULL AND owner_user_id IS NULL) OR "
        "(family_id IS NULL AND owner_user_id IS NOT NULL)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
