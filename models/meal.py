# models/meal.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from core.db import Base
from sqlalchemy.orm import relationship

class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    family = relationship("Family", back_populates="meals", lazy="selectin")  # if you define the reverse
    created_by = relationship("User", back_populates="meals_created", lazy="selectin")

    name = Column(String(255), nullable=False)
    image = Column(String(32), nullable=True)
    calories = Column(Integer, nullable=False)

    prep_time = Column(Integer, nullable=True)
    cook_time = Column(Integer, nullable=True)
    total_time = Column(Integer, nullable=True)

    meal_type = Column(Enum("Breakfast", "Lunch", "Dinner", "Snack", "Dessert", name="mealtype"), nullable=False)
    cuisine = Column(String(120), nullable=True)

    tags = Column(JSONB, nullable=True, default=list)
    macros = Column(JSONB, nullable=True, default=dict)
    difficulty = Column(Enum("Easy", "Medium", "Hard", name="mealdifficulty"), nullable=True)
    servings = Column(Integer, nullable=True)

    diet_compatibility = Column(JSONB, nullable=True, default=list)
    goal_fit = Column(JSONB, nullable=True, default=list)

    ingredients = Column(JSONB, nullable=False, default=list)
    instructions = Column(JSONB, nullable=False, default=list)
    cooking_tools = Column(JSONB, nullable=True, default=list)

    notes = Column(Text, nullable=True, default="")
    is_favorite = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)