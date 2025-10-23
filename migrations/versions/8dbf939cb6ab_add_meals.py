"""add meals

Revision ID: 8dbf939cb6ab
Revises: 9e51c7e68187
Create Date: 2025-10-13 17:08:59.969174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8dbf939cb6ab'
down_revision: Union[str, Sequence[str], None] = '9e51c7e68187'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    meal_type = sa.Enum("Breakfast", "Lunch", "Dinner", "Snack", "Dessert", name="mealtype")
    difficulty = sa.Enum("Easy", "Medium", "Hard", name="mealdifficulty")
    meal_type.create(op.get_bind(), checkfirst=True)
    difficulty.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "meals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("family_id", sa.Integer, sa.ForeignKey("families.id"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),

        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("image", sa.String(16), nullable=False),  # emoji or short string
        sa.Column("calories", sa.Integer, nullable=False),

        sa.Column("prep_time", sa.Integer, nullable=False),
        sa.Column("cook_time", sa.Integer, nullable=False),
        sa.Column("total_time", sa.Integer, nullable=False),

        sa.Column("cuisine", sa.String(120), nullable=False),

        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("macros", postgresql.JSONB, nullable=False, server_default='{"protein":0,"fats":0,"carbs":0}'),
        sa.Column("servings", sa.Integer, nullable=False),

        sa.Column("diet_compatibility", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("goal_fit", postgresql.JSONB, nullable=False, server_default="[]"),

        # array of objects: [{name, amount, inPantry}]
        sa.Column("ingredients", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("instructions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("cooking_tools", postgresql.JSONB, nullable=False, server_default="[]"),

        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("is_favorite", sa.Boolean, nullable=False, server_default=sa.text("false")),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

def downgrade():
    op.drop_table("meals")
    op.execute("DROP TYPE IF EXISTS mealtype")
    op.execute("DROP TYPE IF EXISTS mealdifficulty")