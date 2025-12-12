"""add nutrition and macro fields to user_preferences

Revision ID: 6c8fbe1aca82
Revises: c2fddefaa04c
Create Date: 2025-12-12 10:49:05.725772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6c8fbe1aca82'
down_revision: Union[str, Sequence[str], None] = 'c2fddefaa04c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nutrition and macro fields to user_preferences table."""
    # Basic body information
    op.add_column('user_preferences', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('user_preferences', sa.Column('gender', sa.Text(), nullable=True))
    op.add_column('user_preferences', sa.Column('height_cm', sa.Float(), nullable=True))
    op.add_column('user_preferences', sa.Column('weight_kg', sa.Float(), nullable=True))

    # Dietary preferences
    op.add_column('user_preferences', sa.Column('diet_type', sa.Text(), nullable=True))
    op.add_column('user_preferences', sa.Column('food_allergies', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False))

    # Macro targets in grams
    op.add_column('user_preferences', sa.Column('protein_grams', sa.Float(), nullable=True))
    op.add_column('user_preferences', sa.Column('carb_grams', sa.Float(), nullable=True))
    op.add_column('user_preferences', sa.Column('fat_grams', sa.Float(), nullable=True))

    # Macro targets in calories (optional, for fast UI rendering)
    op.add_column('user_preferences', sa.Column('protein_calories', sa.Float(), nullable=True))
    op.add_column('user_preferences', sa.Column('carb_calories', sa.Float(), nullable=True))
    op.add_column('user_preferences', sa.Column('fat_calories', sa.Float(), nullable=True))

    # Safety/adjustment range
    op.add_column('user_preferences', sa.Column('calorie_min', sa.Integer(), nullable=True))
    op.add_column('user_preferences', sa.Column('calorie_max', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove nutrition and macro fields from user_preferences table."""
    op.drop_column('user_preferences', 'calorie_max')
    op.drop_column('user_preferences', 'calorie_min')
    op.drop_column('user_preferences', 'fat_calories')
    op.drop_column('user_preferences', 'carb_calories')
    op.drop_column('user_preferences', 'protein_calories')
    op.drop_column('user_preferences', 'fat_grams')
    op.drop_column('user_preferences', 'carb_grams')
    op.drop_column('user_preferences', 'protein_grams')
    op.drop_column('user_preferences', 'food_allergies')
    op.drop_column('user_preferences', 'diet_type')
    op.drop_column('user_preferences', 'weight_kg')
    op.drop_column('user_preferences', 'height_cm')
    op.drop_column('user_preferences', 'gender')
    op.drop_column('user_preferences', 'age')
