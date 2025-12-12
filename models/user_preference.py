 # models/user_preference.py
from sqlalchemy import Boolean, Integer, Float, Text, ForeignKey, DateTime, func, text
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

    # ──────────────────────────────────────────────────────────────────────────
    # Basic Body Information (normalized, stored in metric)
    # ──────────────────────────────────────────────────────────────────────────
    age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    gender: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    height_cm: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Dietary & Lifestyle Preferences
    # ──────────────────────────────────────────────────────────────────────────
    # Legacy: array of diet codes (kept for backward compatibility)
    diet_codes: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
    )
    # Single diet type: halal, kosher, vegetarian, vegan, pescatarian
    diet_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Legacy: allergen ingredient IDs (kept for backward compatibility)
    allergen_ingredient_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        server_default="{}",
    )
    # Food allergies as string array (e.g., ["peanuts", "milk", "eggs"])
    food_allergies: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
    )
    disliked_ingredient_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        server_default="{}",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Goal & Athlete Settings
    # ──────────────────────────────────────────────────────────────────────────
    # Goals: lose_weight, get_leaner, balanced, muscle_gain, gain_weight
    goal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'balanced'"),
    )
    # Athlete mode toggle
    is_athlete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    # Training level: light, casual, intense (required if is_athlete=true)
    training_level: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Computed Nutrition Targets (calculated during onboarding/updates)
    # ──────────────────────────────────────────────────────────────────────────
    # Primary calorie target
    calorie_target: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("2000"),
    )
    # Macro targets in grams
    protein_grams: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    carb_grams: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    fat_grams: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    # Macro targets in calories (optional, for fast UI rendering)
    protein_calories: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    carb_calories: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    fat_calories: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Safety & Adjustment Range
    # ──────────────────────────────────────────────────────────────────────────
    # Defines the safe calorie adjustment range shown in UI (+ / − controls)
    calorie_min: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    calorie_max: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Timestamps
    # ──────────────────────────────────────────────────────────────────────────
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
