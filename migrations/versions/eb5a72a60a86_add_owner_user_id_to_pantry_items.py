from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'eb5a72a60a86'
down_revision: Union[str, Sequence[str], None] = 'bc34e6bd7070'
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Column
    cols = {c["name"] for c in insp.get_columns("pantry_items")}
    if "owner_user_id" not in cols:
        op.add_column(
            "pantry_items",
            sa.Column("owner_user_id", sa.Integer(), nullable=True),
        )

    # refresh inspector data after potential schema change
    insp = sa.inspect(bind)

    # 2) Index
    idx_names = {i["name"] for i in insp.get_indexes("pantry_items")}
    if "ix_pantry_items_owner_user_id" not in idx_names:
        op.create_index(
            "ix_pantry_items_owner_user_id",
            "pantry_items",
            ["owner_user_id"],
        )

    # 3) Foreign Key
    fk_names = {fk["name"] for fk in insp.get_foreign_keys("pantry_items")}
    if "fk_pantry_items_owner_user_id_users" not in fk_names:
        op.create_foreign_key(
            "fk_pantry_items_owner_user_id_users",
            source_table="pantry_items",
            referent_table="users",
            local_cols=["owner_user_id"],
            remote_cols=["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop FK if it exists
    fk_names = {fk["name"] for fk in insp.get_foreign_keys("pantry_items")}
    if "fk_pantry_items_owner_user_id_users" in fk_names:
        op.drop_constraint("fk_pantry_items_owner_user_id_users", "pantry_items", type_="foreignkey")

    # Drop index if it exists
    idx_names = {i["name"] for i in insp.get_indexes("pantry_items")}
    if "ix_pantry_items_owner_user_id" in idx_names:
        op.drop_index("ix_pantry_items_owner_user_id", table_name="pantry_items")

    # Drop column if it exists
    cols = {c["name"] for c in insp.get_columns("pantry_items")}
    if "owner_user_id" in cols:
        op.drop_column("pantry_items", "owner_user_id")