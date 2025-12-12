 # models/user_preference.py
from sqlalchemy import Boolean, Integer, Text, ForeignKey, DateTime, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.db import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # one-to-one: each user has exactly one preference row
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Default to empty arrays so preferences are never NULL
    diet_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
    )
    allergen_ingredient_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        server_default="{}",
    )
    disliked_ingredient_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        server_default="{}",
    )

    # Reasonable defaults so a created user always has a full preferences object
    # goals could be: weight_loss | muscle_gain | maintenance | balanced
    goal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'balanced'"),
    )
    calorie_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("2000"),
    )
    is_athlete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    training_level: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # relationships
    user = relationship("User", back_populates="preference", uselist=False)

    def __repr__(self) -> str:
        return f"<UserPreference id={self.id} user_id={self.user_id}>"
