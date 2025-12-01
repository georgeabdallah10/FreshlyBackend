"""add tier to users

Revision ID: 9d8175113336
Revises: d8a355dfb48b
Create Date: 2025-12-01 11:01:32.628746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d8175113336'
down_revision: Union[str, Sequence[str], None] = 'd8a355dfb48b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column(
        "users",
        sa.Column("tier", sa.String(length=32), nullable=False, server_default="free"),
    )

def downgrade():
    op.drop_column("users", "tier")