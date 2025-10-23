"""add recipe_diet_tags join table

Revision ID: a7b3a8b5cf0e
Revises: 6fe3ff011665
Create Date: 2025-09-25 08:38:43.498308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b3a8b5cf0e'
down_revision: Union[str, Sequence[str], None] = '6fe3ff011665'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        "recipe_diet_tags",
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("diet_tag_id", sa.Integer(), sa.ForeignKey("diet_tags.id", ondelete="CASCADE"), primary_key=True),
    )

def downgrade():
    op.drop_table("recipe_diet_tags")