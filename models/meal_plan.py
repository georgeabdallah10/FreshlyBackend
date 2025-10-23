# models/meal_plan.py
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Integer, Text, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from core.db import Base
from .grocery_list import GroceryList


class MealPlan(Base):
    __tablename__ = "meal_plans"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # allow personal plans (no family) -> nullable=True
    family_id: Mapped[int | None] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    family = relationship("Family", back_populates="meal_plans", lazy="selectin")
    created_by = relationship(
        "User",
        back_populates="created_meal_plans",
        foreign_keys=[created_by_user_id],  # disambiguate join
        lazy="selectin",
    )
    slots = relationship("MealSlot", back_populates="meal_plan", cascade="all, delete-orphan", lazy="selectin")
    grocery_lists: Mapped[list["GroceryList"]] = relationship(
        "GroceryList",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ensure collections aren't None on fresh instances
        if getattr(self, "slots", None) is None:
            self.slots = []
        if getattr(self, "grocery_lists", None) is None:
            self.grocery_lists = []

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

    meal_plan = relationship("MealPlan", back_populates="slots", lazy="selectin")
    meals = relationship("MealSlotMeal", back_populates="meal_slot", cascade="all, delete-orphan", lazy="selectin")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if getattr(self, "meals", None) is None:
            self.meals = []

    def __repr__(self) -> str:
        return f"<MealSlot id={self.id} day={self.day} slot={self.slot!r}>"



class MealSlotMeal(Base):
    __tablename__ = "meal_slot_meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_slot_id: Mapped[int] = mapped_column(ForeignKey("meal_slots.id", ondelete="CASCADE"), nullable=False)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), nullable=False)
    portions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    meal_slot = relationship("MealSlot", back_populates="meals", lazy="selectin")
    meal = relationship("Meal", lazy="selectin")

    def __repr__(self) -> str:
        return f"<MealSlotMeal id={self.id} meal_slot_id={self.meal_slot_id} meal_id={self.meal_id}>"