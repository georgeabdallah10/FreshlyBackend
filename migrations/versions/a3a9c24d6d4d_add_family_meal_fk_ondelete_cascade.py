"""Ensure meals.family_id cascades on family delete."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a3a9c24d6d4d"
down_revision: Union[str, Sequence[str], None] = "add_related_share_request_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_family_fk_name(inspector) -> str | None:
    """Locate the FK from meals.family_id -> families.id."""
    for fk in inspector.get_foreign_keys("meals"):
        if (
            fk.get("referred_table") == "families"
            and "family_id" in fk.get("constrained_columns", [])
        ):
            return fk.get("name")
    return None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "meals" not in inspector.get_table_names():
        return

    fk_name = _get_family_fk_name(inspector)
    create_name = fk_name or "meals_family_id_fkey"

    with op.batch_alter_table("meals") as batch_op:
        if fk_name:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            create_name,
            "families",
            ["family_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "meals" not in inspector.get_table_names():
        return

    fk_name = _get_family_fk_name(inspector)
    create_name = fk_name or "meals_family_id_fkey"

    with op.batch_alter_table("meals") as batch_op:
        if fk_name:
            batch_op.drop_constraint(fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            create_name,
            "families",
            ["family_id"],
            ["id"],
        )
