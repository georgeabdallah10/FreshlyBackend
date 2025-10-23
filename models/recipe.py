# models/recipe.py
from sqlalchemy import Integer, Text, DateTime, ForeignKey, func, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base

# Association table for many-to-many between recipes and diet_tags
recipe_diet_tags = Table(
    "recipe_diet_tags",
    Base.metadata,
    Column("recipe_id", ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
    Column("diet_tag_id", ForeignKey("diet_tags.id", ondelete="CASCADE"), primary_key=True),
)


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # relationships
    family = relationship("Family", back_populates="recipes", lazy="selectin")
    ingredients = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    diet_tags = relationship(
        "DietTag",
        secondary=recipe_diet_tags,
        back_populates="recipes",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Recipe id={self.id} title={self.title!r} family_id={self.family_id}>"