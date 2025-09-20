# models/diet_tag.py
from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base


class DietTag(Base):
    __tablename__ = "diet_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)       # e.g., vegan, gluten_free
    display_name: Mapped[str] = mapped_column(Text, nullable=False)            # e.g., Vegan

    # relationships
    recipes = relationship("RecipeDietTag", back_populates="diet_tag", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DietTag id={self.id} code={self.code!r}>"