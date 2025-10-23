"""make family_id nullable + check

Revision ID: 9e51c7e68187
Revises: 6bc299328adb
Create Date: 2025-10-13 11:40:23.035922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e51c7e68187'
down_revision: Union[str, Sequence[str], None] = '6bc299328adb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) family_id can be NULL (for personal items)
    op.alter_column(
        "pantry_items",
        "family_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 2) Add a CHECK: at least one of (family_id, owner_user_id) must be set
    op.create_check_constraint(
        "pantry_items_owner_or_family_ck",
        "pantry_items",
        "(family_id IS NOT NULL) OR (owner_user_id IS NOT NULL)",
    )
def downgrade():
    # drop the check
    op.drop_constraint(
        "pantry_items_owner_or_family_ck",
        "pantry_items",
        type_="check",
    )
    # revert to NOT NULL (will fail if rows exist with NULL family_id)
    op.alter_column(
        "pantry_items",
        "family_id",
        existing_type=sa.Integer(),
        nullable=False,
    )