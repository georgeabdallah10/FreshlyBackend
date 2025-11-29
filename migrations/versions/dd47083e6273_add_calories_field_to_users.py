"""add calories field to users

Revision ID: dd47083e6273
Revises: 8167ab6fda78
Create Date: 2025-11-27 22:24:58.517207
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "dd47083e6273"
down_revision: Union[str, Sequence[str], None] = "8167ab6fda78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------------------------
    # IMPORTANT:
    # Your database *does not* currently have:
    #   - meal_share_requests
    #   - notifications
    #
    # These DROP statements were incorrectly included because earlier migrations did not
    # run due to Supabase pooler restrictions.
    #
    # So we REMOVE these operations to avoid errors like:
    #   psycopg2.errors.UndefinedTable: table "meal_share_requests" does not exist
    #
    # When we remove these, Alembic can continue and later migrations will properly
    # CREATE the missing tables.
    # ------------------------------------------------------------------------------------

    # ❌ REMOVE BAD OPERATIONS (DO NOT DROP NON-EXISTENT TABLES)
    # op.drop_table("meal_share_requests")
    # op.drop_index(op.f("ix_notifications_created_at"), table_name="notifications")
    # op.drop_index(
    #     op.f("ix_notifications_user_unread"),
    #     table_name="notifications",
    #     postgresql_where="(is_read = false)",
    # )
    # op.drop_table("notifications")

    # ✔ KEEP ONLY THE VALID MIGRATION PART
    op.add_column("users", sa.Column("calories", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Only remove the calories column
    op.drop_column("users", "calories")

    # NOTE:
    # We DO NOT recreate notifications or meal_share_requests here.
    # Their creation is handled in earlier migrations.
    #
    # This keeps downgrade consistent with your real schema state.