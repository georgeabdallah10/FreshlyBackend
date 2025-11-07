"""Add related_share_request_id to notifications"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

# Revision identifiers
revision: str = "add_related_share_request_id"
down_revision: Union[str, Sequence[str], None] = "10692832808e"  # your current head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing column with FK
    op.add_column(
        "notifications",
        sa.Column("related_share_request_id", sa.Integer(), nullable=True)
    )
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "meal_share_requests" in inspector.get_table_names():
        op.create_foreign_key(
            "fk_notifications_related_share_request_id",
            "notifications",
            "meal_share_requests",
            ["related_share_request_id"],
            ["id"],
            ondelete="SET NULL"
        )
    else:
        print("⚠️ Skipping foreign key creation: meal_share_requests table does not exist.")


def downgrade() -> None:
    # Drop foreign key + column
    op.drop_constraint("fk_notifications_related_share_request_id", "notifications", type_="foreignkey")
    op.drop_column("notifications", "related_share_request_id")