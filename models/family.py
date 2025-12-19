# models/family.py
from __future__ import annotations

from typing import List
from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, relationship, mapped_column
from .recipe import Recipe
from .meal_plan import MealPlan
from .pantry_item import PantryItem
from .grocery_list import GroceryList
from .membership import FamilyMembership

from core.db import Base


class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    invite_code: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # many-to-one from Recipe -> Family, back to here
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe",
        back_populates="family",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # one-to-many Family -> MealPlan (back_populates on MealPlan.family)
    meal_plans: Mapped[List["MealPlan"]] = relationship(
        "MealPlan",
        back_populates="family",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # Meals inherit cascade delete at the DB level (FK ON DELETE CASCADE)
    meals: Mapped[List["Meal"]] = relationship(
        "Meal",
        back_populates="family",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # one-to-many Family -> PantryItem (back_populates on PantryItem.family)
    pantry_items: Mapped[List["PantryItem"]] = relationship(
        "PantryItem",
        back_populates="family",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # one-to-many Family -> GroceryList (back_populates on GroceryList.family)
    grocery_lists: Mapped[List["GroceryList"]] = relationship(
        "GroceryList",
        back_populates="family",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # memberships (user<->family join table)
    memberships: Mapped[List["FamilyMembership"]] = relationship(
        "FamilyMembership",
        back_populates="family",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Family id={self.id} name={self.display_name!r}>"
