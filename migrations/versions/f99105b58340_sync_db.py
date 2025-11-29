from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision = "f99105b58340"
down_revision = "23e192dcb65b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----- ENUM FIX -----
    # meal_share_request_status already exists, so reuse it
    meal_share_status_enum = ENUM(
        "pending", "accepted", "declined",
        name="meal_share_request_status",
        create_type=False
    )

    # notification_type DOES NOT EXIST, so create it before using it
    notification_type_enum = ENUM(
        "meal_share_request",
        "meal_share_accepted",
        "meal_share_declined",
        "family_invite",
        "family_member_joined",
        "system",
        name="notification_type",
        create_type=True  # <-- CREATE THIS ENUM
    )

    # Actually create enum in DB
    notification_type_enum.create(op.get_bind(), checkfirst=True)

    # ----- Meal Share Requests table -----
    op.create_table(
        "meal_share_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meal_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("accepted_meal_id", sa.Integer(), nullable=True),
        sa.Column("status", meal_share_status_enum, nullable=False),
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

    # ----- Notifications table -----
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_meal_id", sa.Integer(), nullable=True),
        sa.Column("related_user_id", sa.Integer(), nullable=True),
        sa.Column("related_family_id", sa.Integer(), nullable=True),
        sa.Column("related_share_request_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_share_request_id"], ["meal_share_requests.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("meal_share_requests")

    # clean up enum only if exists
    ENUM(name="notification_type").drop(op.get_bind(), checkfirst=True)