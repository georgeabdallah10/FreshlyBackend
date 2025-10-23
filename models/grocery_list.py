# models/grocery_list.py
from sqlalchemy import Integer, Text, DateTime, ForeignKey, Numeric, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base
from datetime import datetime
from decimal import Decimal


class GroceryList(Base):
    __tablename__ = "grocery_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    meal_plan_id: Mapped[int | None] = mapped_column(ForeignKey("meal_plans.id", ondelete="SET NULL"))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")  # draft | finalized | purchased
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    family = relationship("Family", back_populates="grocery_lists")
    meal_plan = relationship("MealPlan", back_populates="grocery_lists")
    items = relationship("GroceryListItem", back_populates="grocery_list", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<GroceryList id={self.id} family_id={self.family_id} status={self.status}>"


class GroceryListItem(Base):
    __tablename__ = "grocery_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grocery_list_id: Mapped[int] = mapped_column(ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True)
    checked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    grocery_list = relationship("GroceryList", back_populates="items")
    ingredient = relationship("Ingredient")
    unit = relationship("Unit")

    def __repr__(self) -> str:
        return f"<GroceryListItem id={self.id} ingredient_id={self.ingredient_id} checked={self.checked}>"