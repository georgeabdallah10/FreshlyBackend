"""add_age_weight_height_to_users

Revision ID: ed615402307a
Revises: add_oauth_accounts_table
Create Date: 2025-11-15 19:20:36.905458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed615402307a'
down_revision: Union[str, Sequence[str], None] = 'add_oauth_accounts_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("age", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("weight", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("height", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("height")
        batch_op.drop_column("weight")
        batch_op.drop_column("age")
