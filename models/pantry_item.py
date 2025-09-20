# models/pantry_item.py
from sqlalchemy import Integer, DateTime, Date, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base
from datetime import date, datetime
from decimal import Decimal


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True)
    expires_at: Mapped[date| None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # relationships
    family = relationship("Family", back_populates="pantry_items")
    ingredient = relationship("Ingredient")
    unit = relationship("Unit")

    def __repr__(self) -> str:
        return f"<PantryItem id={self.id} ingredient_id={self.ingredient_id} family_id={self.family_id}>"