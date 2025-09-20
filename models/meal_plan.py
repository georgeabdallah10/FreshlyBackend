# models/meal_plan.py
from sqlalchemy import Integer, Text, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base
from typing import Optional
from sqlalchemy import Date


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    week_start: Mapped["Date"] = mapped_column(Date, nullable=False)
    week_end: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)    
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    family = relationship("Family", back_populates="meal_plans")
    created_by_user = relationship("User", back_populates="meal_plans")
    slots = relationship("MealSlot", back_populates="meal_plan", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MealPlan id={self.id} title={self.title!r} family_id={self.family_id}>"


class MealSlot(Base):
    __tablename__ = "meal_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_plan_id: Mapped[int] = mapped_column(ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)  # 0–6
    slot: Mapped[str] = mapped_column(Text, nullable=False)    # breakfast | lunch | dinner | snack
    servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    meal_plan = relationship("MealPlan", back_populates="slots")
    recipes = relationship("MealSlotRecipe", back_populates="meal_slot", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<MealSlot id={self.id} day={self.day} slot={self.slot!r}>"


class MealSlotRecipe(Base):
    __tablename__ = "meal_slot_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_slot_id: Mapped[int] = mapped_column(ForeignKey("meal_slots.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    portions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # relationships
    meal_slot = relationship("MealSlot", back_populates="recipes")
    recipe = relationship("Recipe")

    def __repr__(self) -> str:
        return f"<MealSlotRecipe id={self.id} meal_slot_id={self.meal_slot_id} recipe_id={self.recipe_id}>"