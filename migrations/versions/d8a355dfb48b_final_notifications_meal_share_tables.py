"""final notifications + meal share tables

Revision ID: d8a355dfb48b
Revises: 23e192dcb65b
Create Date: 2025-11-28 22:28:50.834114
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision = "d8a355dfb48b"
down_revision = "23e192dcb65b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Reuse existing enums ---
    meal_share_status = ENUM(
        "pending",
        "accepted",
        "declined",
        name="meal_share_request_status",
        create_type=False,
    )

    notification_type = ENUM(
        "meal_share_request",
        "meal_share_accepted",
        "meal_share_declined",
        "family_invite",
        "family_member_joined",
        "system",
        name="notification_type",
        create_type=False,
    )

    # --- Create meal_share_requests table ---
    op.create_table(
        "meal_share_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("meal_id", sa.Integer, nullable=False),
        sa.Column("sender_user_id", sa.Integer, nullable=False),
        sa.Column("recipient_user_id", sa.Integer, nullable=False),
        sa.Column("family_id", sa.Integer, nullable=True),
        sa.Column("accepted_meal_id", sa.Integer, nullable=True),
        sa.Column("status", meal_share_status, nullable=False),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),

        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accepted_meal_id"], ["meals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
    )

    # --- Create notifications table ---
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_meal_id", sa.Integer, nullable=True),
        sa.Column("related_user_id", sa.Integer, nullable=True),
        sa.Column("related_family_id", sa.Integer, nullable=True),
        sa.Column("related_share_request_id", sa.Integer, nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_share_request_id"], ["meal_share_requests.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("meal_share_requests")