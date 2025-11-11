"""Allow sharing meals outside families and track accepted copies."""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "global_meal_sharing_support"
down_revision: Union[str, Sequence[str], None] = "create_meal_share_requests_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "meal_share_requests" not in inspector.get_table_names():
        print("⚠️ Skipping upgrade: meal_share_requests table does not exist.")
        return

    columns = {col["name"] for col in inspector.get_columns("meal_share_requests")}

    with op.batch_alter_table("meal_share_requests") as batch_op:
        batch_op.alter_column(
            "family_id",
            existing_type=sa.Integer(),
            nullable=True
        )

        if "accepted_meal_id" not in columns:
            batch_op.add_column(sa.Column("accepted_meal_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_meal_share_requests_accepted_meal_id",
                "meals",
                ["accepted_meal_id"],
                ["id"],
                ondelete="SET NULL"
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "meal_share_requests" not in inspector.get_table_names():
        print("⚠️ Skipping downgrade: meal_share_requests table does not exist.")
        return

    columns = {col["name"] for col in inspector.get_columns("meal_share_requests")}

    with op.batch_alter_table("meal_share_requests") as batch_op:
        if "accepted_meal_id" in columns:
            batch_op.drop_constraint(
                "fk_meal_share_requests_accepted_meal_id",
                type_="foreignkey"
            )
            batch_op.drop_column("accepted_meal_id")

        batch_op.alter_column(
            "family_id",
            existing_type=sa.Integer(),
            nullable=False
        )
