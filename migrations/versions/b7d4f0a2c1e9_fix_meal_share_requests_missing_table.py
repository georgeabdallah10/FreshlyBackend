"""fix_meal_share_requests_missing_table

Revision ID: b7d4f0a2c1e9
Revises: ec785f0856c7
Create Date: 2025-11-04 18:25:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d4f0a2c1e9'
down_revision: Union[str, Sequence[str], None] = 'ec785f0856c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure enum and table exist even if prior migration was partially applied."""
    conn = op.get_bind()

    # ✅ Safely create the enum if it doesn't exist
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'meal_share_request_status') THEN
                CREATE TYPE meal_share_request_status AS ENUM ('pending', 'accepted', 'declined');
            END IF;
        END$$;
    """))

    # ✅ Create the table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS meal_share_requests (
            id SERIAL PRIMARY KEY,
            meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
            sender_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            recipient_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
            status meal_share_request_status NOT NULL DEFAULT 'pending',
            message VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            responded_at TIMESTAMPTZ
        );
    """)

    # ✅ Create indexes if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_meal_share_requests_recipient_user_id ON meal_share_requests (recipient_user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_meal_share_requests_sender_user_id ON meal_share_requests (sender_user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_meal_share_requests_status ON meal_share_requests (status);")


def downgrade() -> None:
    """Safely remove meal_share_requests table and enum."""
    conn = op.get_bind()

    # ✅ Drop indexes safely
    op.execute("DROP INDEX IF EXISTS ix_meal_share_requests_status;")
    op.execute("DROP INDEX IF EXISTS ix_meal_share_requests_sender_user_id;")
    op.execute("DROP INDEX IF EXISTS ix_meal_share_requests_recipient_user_id;")

    # ✅ Drop table safely
    op.execute("DROP TABLE IF EXISTS meal_share_requests;")

    # ✅ Drop enum type only if unused
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type t
                LEFT JOIN pg_class c ON t.oid = c.reltype
                WHERE t.typname = 'meal_share_request_status' AND c.relname IS NOT NULL
            ) THEN
                DROP TYPE IF EXISTS meal_share_request_status;
            END IF;
        END$$;
    """))
