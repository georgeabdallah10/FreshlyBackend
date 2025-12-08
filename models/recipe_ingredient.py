# models/recipe_ingredient.py
from sqlalchemy import Integer, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base
from decimal import Decimal


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True)

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
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient")
    unit = relationship("Unit")

    def __repr__(self) -> str:
        return f"<RecipeIngredient id={self.id} recipe_id={self.recipe_id} ingredient_id={self.ingredient_id}>"
