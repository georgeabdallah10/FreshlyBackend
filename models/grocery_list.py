# models/grocery_list.py
from sqlalchemy import Integer, Text, DateTime, ForeignKey, Numeric, Boolean, CheckConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base
from datetime import datetime
from decimal import Decimal


class GroceryList(Base):
    __tablename__ = "grocery_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Dual-scope fields (XOR constraint)
    family_id: Mapped[int | None] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Creator tracking (for pantry sync permissions)
    # For family lists, only the creator can sync with pantry
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    meal_plan_id: Mapped[int | None] = mapped_column(ForeignKey("meal_plans.id", ondelete="SET NULL"))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")  # draft | finalized | purchased
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # relationships
    family = relationship("Family", back_populates="grocery_lists")
    owner = relationship("User", back_populates="personal_grocery_lists", foreign_keys=[owner_user_id])
    creator = relationship("User", foreign_keys=[created_by_user_id])
    meal_plan = relationship("MealPlan", back_populates="grocery_lists")
    items = relationship("GroceryListItem", back_populates="grocery_list", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "(family_id IS NOT NULL AND owner_user_id IS NULL) OR "
            "(family_id IS NULL AND owner_user_id IS NOT NULL)",
            name="grocery_list_scope_xor"
        ),
        Index('idx_grocery_list_family_status', 'family_id', 'status'),
        Index('idx_grocery_list_owner_status', 'owner_user_id', 'status'),
    )

    def __repr__(self) -> str:
        scope = "family" if self.family_id else "personal"
        return f"<GroceryList id={self.id} scope={scope} status={self.status}>"


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