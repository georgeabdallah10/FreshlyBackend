"""Create meal_share_requests table"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union

revision: str = "create_meal_share_requests_table"
down_revision: Union[str, Sequence[str], None] = "add_related_share_request_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum handling
    conn = op.get_bind()
    existing_enums = conn.execute(
        sa.text("SELECT typname FROM pg_type WHERE typname = 'meal_share_request_status'")
    ).fetchall()
    if not existing_enums:
        status_enum = sa.Enum("pending", "accepted", "declined", name="meal_share_request_status")
        status_enum.create(conn, checkfirst=True)
    else:
        print("⚠️ Enum 'meal_share_request_status' already exists, reusing existing type.")
        status_enum = sa.Enum(name="meal_share_request_status", metadata=sa.MetaData())

    # Create meal_share_requests table
    op.create_table(
        "meal_share_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meal_id", sa.Integer(), sa.ForeignKey("meals.id", ondelete="CASCADE")),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("family_id", sa.Integer(), sa.ForeignKey("families.id", ondelete="SET NULL")),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("meal_share_requests")
    sa.Enum(name="meal_share_request_status").drop(op.get_bind(), checkfirst=True)