"""add athlete fields to user_preferences

Revision ID: c2fddefaa04c
Revises: a1b2c3d4e5f6
Create Date: 2025-12-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2fddefaa04c"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "is_athlete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "training_level",
            sa.Text(),
            nullable=True,
        ),
    )
    op.execute("UPDATE user_preferences SET is_athlete = false, training_level = NULL")


def downgrade() -> None:
    op.drop_column("user_preferences", "training_level")
    op.drop_column("user_preferences", "is_athlete")
