# models/diet_tag.py
from __future__ import annotations
from typing import List
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.recipe import Recipe
from core.db import Base


class DietTag(Base):
    __tablename__ = "diet_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)       # e.g., vegan, gluten_free
    display_name: Mapped[str] = mapped_column(Text, nullable=False)            # e.g., Vegan

    # relationships
    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe",
        secondary="recipe_diet_tags",
        back_populates="diet_tags",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DietTag id={self.id} code={self.code!r}>"