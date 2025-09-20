# models/unit.py
from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from core.db import Base


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)          # e.g., g, ml, cup
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)         # e.g., gram
    is_metric: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<Unit id={self.id} code={self.code!r} metric={self.is_metric}>"