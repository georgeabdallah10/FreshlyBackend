# models/pantry_item.py
from sqlalchemy import Integer, DateTime, Date, ForeignKey, Numeric, func, String, Column, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), nullable=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=True)
    ingredient = relationship("Ingredient", back_populates="pantry_items")
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit = Column(String(64), nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Generated image URL

    # Normalized quantity fields for unit-agnostic comparisons
    canonical_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
        comment="Quantity normalized to ingredient's canonical unit"
    )
    canonical_unit: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="Canonical unit code (g, ml, count)"
    )

    # relationships
    family = relationship("Family", back_populates="pantry_items")

    owner = relationship("User", back_populates="personal_pantry_items")

    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<PantryItem id={self.id} ingredient_id={self.ingredient_id} family_id={self.family_id}>"

    __table_args__ = (
        CheckConstraint(
            "(family_id IS NOT NULL AND owner_user_id IS NULL) OR (family_id IS NULL AND owner_user_id IS NOT NULL)",
            name="pantry_scope_xor"
        ),
        # Composite indexes for common query patterns
        Index('idx_pantry_family_expires', 'family_id', 'expires_at'),
        Index('idx_pantry_owner_expires', 'owner_user_id', 'expires_at'),
    )
