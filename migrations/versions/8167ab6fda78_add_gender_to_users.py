"""add_gender_to_users

Revision ID: 8167ab6fda78
Revises: ed615402307a
Create Date: 2025-11-15 19:51:07.361405

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8167ab6fda78'
down_revision: Union[str, Sequence[str], None] = 'ed615402307a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("gender", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("gender")
