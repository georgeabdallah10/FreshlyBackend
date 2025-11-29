"""sync db

Revision ID: f99105b58340
Revises: 23e192dcb65b
Create Date: 2025-11-28 22:23:42.675325
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = "f99105b58340"
down_revision: Union[str, Sequence[str], None] = "23e192dcb65b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---- IMPORTANT: Use existing enum types, DO NOT create them ----
    meal_share_status_enum = ENUM(
        "pending",
        "accepted",
        "declined",
        name="meal_share_request_status",
        create_type=False,
    )

    notification_type_enum = ENUM(
        "meal_share_request",
        "meal_share_accepted",
        "meal_share_declined",
        "family_invite",
        "family_member_joined",
        "system",
        name="notification_type",
        create_type=False,
    )

    # ---- Meal Share Requests ----
    op.create_table(
        "meal_share_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meal_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("accepted_meal_id", sa.Integer(), nullable=True),
        sa.Column("status", meal_share_status_enum, nullable=False),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["accepted_meal_id"], ["meals.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )

    # ---- Notifications ----
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_meal_id", sa.Integer(), nullable=True),
        sa.Column("related_user_id", sa.Integer(), nullable=True),
        sa.Column("related_family_id", sa.Integer(), nullable=True),
        sa.Column("related_share_request_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["related_family_id"], ["families.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["related_meal_id"], ["meals.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["related_share_request_id"], ["meal_share_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["related_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("meal_share_requests")