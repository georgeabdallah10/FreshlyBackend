# schemas/user_preference.py
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator, AliasChoices
from typing import Optional, List, Literal, Any
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Type definitions for allowed enum values
# ──────────────────────────────────────────────────────────────────────────────
GenderType = Literal["male", "female"]
TrainingLevelType = Literal["light", "casual", "intense"]
# Accept both hyphenated (frontend) and underscored (canonical) goal values
GoalType = Literal[
    "lose_weight", "get_leaner", "balanced", "muscle_gain", "gain_weight",
    "lose-weight", "leaner", "muscle-gain", "weight-gain"
]
DietTypeType = Literal["halal", "kosher", "vegetarian", "vegan", "pescatarian"]

# Mapping from frontend goal values to canonical backend values
GOAL_NORMALIZATION_MAP = {
    "lose-weight": "lose_weight",
    "leaner": "get_leaner",
    "muscle-gain": "muscle_gain",
    "weight-gain": "gain_weight",
}


class UserPreferenceCreate(BaseModel):
    """Schema for creating user preferences during onboarding."""

    # ──────────────────────────────────────────────────────────────────────────
    # Basic Body Information (normalized, stored in metric)
    # ──────────────────────────────────────────────────────────────────────────
    age: Optional[int] = Field(None, ge=13, description="User's age (must be >= 13)")
    gender: Optional[GenderType] = Field(None, description="User's gender: male or female")
    height_cm: Optional[float] = Field(
        None, ge=100, le=250, description="User's height in cm (100-250)"
    )
    weight_kg: Optional[float] = Field(
        None, ge=30, le=300, description="User's weight in kg (30-300)"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Dietary & Lifestyle Preferences
    # ──────────────────────────────────────────────────────────────────────────
    # Legacy fields (kept for backward compatibility)
    diet_codes: List[str] = Field(
        default_factory=list, description="List of diet codes, e.g. ['vegan','gluten_free']"
    )
    allergen_ingredient_ids: List[int] = Field(
        default_factory=list, description="Ingredient IDs the user is allergic to"
    )
    disliked_ingredient_ids: List[int] = Field(
        default_factory=list, description="Ingredient IDs the user dislikes"
    )
    # New fields
    diet_type: Optional[DietTypeType] = Field(
        None, description="Single diet type: halal, kosher, vegetarian, vegan, pescatarian"
    )
    food_allergies: List[str] = Field(
        default_factory=list,
        description="Food allergies as strings (e.g., ['peanuts', 'milk', 'eggs'])",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Goal & Athlete Settings
    # ──────────────────────────────────────────────────────────────────────────
    goal: GoalType = Field(
        "balanced",
        description="Goal: lose_weight, get_leaner, balanced, muscle_gain, gain_weight",
    )
    # Accept both 'is_athlete' and 'athlete_mode' from frontend
    is_athlete: bool = Field(
        False,
        description="Whether the user is an athlete",
        validation_alias=AliasChoices("is_athlete", "athlete_mode"),
    )
    training_level: Optional[TrainingLevelType] = Field(
        None, description="Training intensity level for athletes: light, casual, intense"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Computed Nutrition Targets
    # ──────────────────────────────────────────────────────────────────────────
    # Accept both 'calorie_target' and 'target_calories' from frontend
    calorie_target: int = Field(
        2000,
        ge=0,
        description="Daily calorie target",
        validation_alias=AliasChoices("calorie_target", "target_calories"),
    )
    protein_grams: Optional[float] = Field(None, ge=0, description="Protein target in grams")
    carb_grams: Optional[float] = Field(None, ge=0, description="Carbohydrate target in grams")
    fat_grams: Optional[float] = Field(None, ge=0, description="Fat target in grams")
    protein_calories: Optional[float] = Field(None, ge=0, description="Protein target in calories")
    carb_calories: Optional[float] = Field(None, ge=0, description="Carbohydrate target in calories")
    fat_calories: Optional[float] = Field(None, ge=0, description="Fat target in calories")

    # ──────────────────────────────────────────────────────────────────────────
    # Safety & Adjustment Range
    # ──────────────────────────────────────────────────────────────────────────
    calorie_min: Optional[int] = Field(None, ge=0, description="Minimum safe calorie target")
    calorie_max: Optional[int] = Field(None, ge=0, description="Maximum safe calorie target")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("goal", mode="before")
    @classmethod
    def normalize_goal(cls, v: Any) -> str:
        """Normalize frontend goal values to canonical backend values."""
        if isinstance(v, str):
            return GOAL_NORMALIZATION_MAP.get(v, v)
        return v

    @model_validator(mode="after")
    def validate_athlete_and_calorie_range(self):
        # Training level validation
        if not self.is_athlete and self.training_level is not None:
            raise ValueError("training_level must be null when is_athlete is false")
        if self.is_athlete and self.training_level is None:
            raise ValueError("training_level is required when is_athlete is true")

        # Calorie range validation
        if self.calorie_min is not None and self.calorie_max is not None:
            if self.calorie_min > self.calorie_max:
                raise ValueError("calorie_min must be <= calorie_max")
            if not (self.calorie_min <= self.calorie_target <= self.calorie_max):
                raise ValueError("calorie_target must be between calorie_min and calorie_max")

        return self


class UserPreferenceUpdate(BaseModel):
    """Schema for partially updating user preferences."""

    # ──────────────────────────────────────────────────────────────────────────
    # Basic Body Information
    # ──────────────────────────────────────────────────────────────────────────
    age: Optional[int] = Field(None, ge=13, description="User's age (must be >= 13)")
    gender: Optional[GenderType] = Field(None, description="User's gender: male or female")
    height_cm: Optional[float] = Field(
        None, ge=100, le=250, description="User's height in cm (100-250)"
    )
    weight_kg: Optional[float] = Field(
        None, ge=30, le=300, description="User's weight in kg (30-300)"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Dietary & Lifestyle Preferences
    # ──────────────────────────────────────────────────────────────────────────
    diet_codes: Optional[List[str]] = Field(
        None, description="List of diet codes, e.g. ['vegan','gluten_free']"
    )
    allergen_ingredient_ids: Optional[List[int]] = Field(
        None, description="Ingredient IDs the user is allergic to"
    )
    disliked_ingredient_ids: Optional[List[int]] = Field(
        None, description="Ingredient IDs the user dislikes"
    )
    diet_type: Optional[DietTypeType] = Field(
        None, description="Single diet type: halal, kosher, vegetarian, vegan, pescatarian"
    )
    food_allergies: Optional[List[str]] = Field(
        None, description="Food allergies as strings (e.g., ['peanuts', 'milk', 'eggs'])"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Goal & Athlete Settings
    # ──────────────────────────────────────────────────────────────────────────
    goal: Optional[GoalType] = Field(
        None, description="Goal: lose_weight, get_leaner, balanced, muscle_gain, gain_weight"
    )
    # Accept both 'is_athlete' and 'athlete_mode' from frontend
    is_athlete: Optional[bool] = Field(
        None,
        description="Whether the user is an athlete",
        validation_alias=AliasChoices("is_athlete", "athlete_mode"),
    )
    training_level: Optional[TrainingLevelType] = Field(
        None, description="Training intensity level for athletes: light, casual, intense"
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Computed Nutrition Targets
    # ──────────────────────────────────────────────────────────────────────────
    # Accept both 'calorie_target' and 'target_calories' from frontend
    calorie_target: Optional[int] = Field(
        None,
        ge=0,
        description="Daily calorie target",
        validation_alias=AliasChoices("calorie_target", "target_calories"),
    )
    protein_grams: Optional[float] = Field(None, ge=0, description="Protein target in grams")
    carb_grams: Optional[float] = Field(None, ge=0, description="Carbohydrate target in grams")
    fat_grams: Optional[float] = Field(None, ge=0, description="Fat target in grams")
    protein_calories: Optional[float] = Field(None, ge=0, description="Protein target in calories")
    carb_calories: Optional[float] = Field(None, ge=0, description="Carbohydrate target in calories")
    fat_calories: Optional[float] = Field(None, ge=0, description="Fat target in calories")

    # ──────────────────────────────────────────────────────────────────────────
    # Safety & Adjustment Range
    # ──────────────────────────────────────────────────────────────────────────
    calorie_min: Optional[int] = Field(None, ge=0, description="Minimum safe calorie target")
    calorie_max: Optional[int] = Field(None, ge=0, description="Maximum safe calorie target")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("goal", mode="before")
    @classmethod
    def normalize_goal(cls, v: Any) -> Optional[str]:
        """Normalize frontend goal values to canonical backend values."""
        if isinstance(v, str):
            return GOAL_NORMALIZATION_MAP.get(v, v)
        return v

    @model_validator(mode="after")
    def validate_athlete_training_level(self):
        # Only validate if both fields are explicitly set
        if self.is_athlete is False and self.training_level is not None:
            raise ValueError("training_level must be null when is_athlete is false")
        if self.is_athlete is True and self.training_level is None:
            raise ValueError("training_level is required when is_athlete is true")
        return self


class UserPreferenceOut(BaseModel):
    """Schema for returning user preferences in API responses."""

    id: int = Field(..., description="Unique identifier of the user preference")
    user_id: int = Field(..., description="User this preference belongs to")

    # ──────────────────────────────────────────────────────────────────────────
    # Basic Body Information
    # ──────────────────────────────────────────────────────────────────────────
    age: Optional[int] = Field(None, description="User's age")
    gender: Optional[str] = Field(None, description="User's gender: male or female")
    height_cm: Optional[float] = Field(None, description="User's height in cm")
    weight_kg: Optional[float] = Field(None, description="User's weight in kg")

    # ──────────────────────────────────────────────────────────────────────────
    # Dietary & Lifestyle Preferences
    # ──────────────────────────────────────────────────────────────────────────
    diet_codes: Optional[List[str]] = Field(None, description="List of diet codes")
    allergen_ingredient_ids: Optional[List[int]] = Field(
        None, description="Ingredient IDs the user is allergic to"
    )
    disliked_ingredient_ids: Optional[List[int]] = Field(
        None, description="Ingredient IDs the user dislikes"
    )
    diet_type: Optional[str] = Field(None, description="Single diet type")
    food_allergies: Optional[List[str]] = Field(None, description="Food allergies as strings")

    # ──────────────────────────────────────────────────────────────────────────
    # Goal & Athlete Settings
    # ──────────────────────────────────────────────────────────────────────────
    goal: Optional[str] = Field(None, description="User's goal")
    is_athlete: bool = Field(..., description="Whether the user is an athlete")
    training_level: Optional[str] = Field(None, description="Training intensity level")

    # ──────────────────────────────────────────────────────────────────────────
    # Computed Nutrition Targets
    # ──────────────────────────────────────────────────────────────────────────
    calorie_target: Optional[int] = Field(None, description="Daily calorie target")
    protein_grams: Optional[float] = Field(None, description="Protein target in grams")
    carb_grams: Optional[float] = Field(None, description="Carbohydrate target in grams")
    fat_grams: Optional[float] = Field(None, description="Fat target in grams")
    protein_calories: Optional[float] = Field(None, description="Protein target in calories")
    carb_calories: Optional[float] = Field(None, description="Carbohydrate target in calories")
    fat_calories: Optional[float] = Field(None, description="Fat target in calories")

    # ──────────────────────────────────────────────────────────────────────────
    # Safety & Adjustment Range
    # ──────────────────────────────────────────────────────────────────────────
    calorie_min: Optional[int] = Field(None, description="Minimum safe calorie target")
    calorie_max: Optional[int] = Field(None, description="Maximum safe calorie target")

    # ──────────────────────────────────────────────────────────────────────────
    # Timestamps
    # ──────────────────────────────────────────────────────────────────────────
    created_at: datetime = Field(..., description="Timestamp when the preference was created")
    updated_at: datetime = Field(..., description="Timestamp when the preference was last updated")

    model_config = ConfigDict(from_attributes=True)
