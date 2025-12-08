# models/ingredient.py
from sqlalchemy import Integer, Text, DateTime, func, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base
import enum


class CanonicalUnitType(str, enum.Enum):
    """Enum for canonical unit types."""
    weight = "weight"
    volume = "volume"
    count = "count"


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Unit normalization fields
    canonical_unit_type: Mapped[str | None] = mapped_column(
        SAEnum(CanonicalUnitType, name="canonical_unit_type_enum", create_constraint=True),
        nullable=True,
        comment="Type of canonical unit: weight, volume, or count"
    )
    canonical_unit: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Canonical unit code: g, ml, count, etc."
    )
    avg_weight_per_unit_g: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Average weight in grams for one unit (e.g., one egg = 50g)"
    )
    density_g_per_ml: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Density in grams per milliliter for volume-to-weight conversion"
    )
    pieces_per_package: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of pieces in a standard package"
    )

    # Relationships
    pantry_items = relationship("PantryItem", back_populates="ingredient")

    def __repr__(self) -> str:
        return f"<Ingredient id={self.id} name={self.name!r} category={self.category!r}>"
