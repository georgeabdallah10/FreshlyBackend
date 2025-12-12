# schemas/user_preference.py
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, List, Literal
from datetime import datetime


class UserPreferenceCreate(BaseModel):
    diet_codes: List[str] = Field(..., description="List of diet codes, e.g. ['vegan','gluten_free']")
    allergen_ingredient_ids: List[int] = Field(..., description="Ingredient IDs the user is allergic to")
    disliked_ingredient_ids: List[int] = Field(..., description="Ingredient IDs the user dislikes")
    goal: str = Field(..., description="Goal preference as any string")
    calorie_target: int = Field(..., ge=0, description="Daily calorie target")
    is_athlete: bool = Field(False, description="Whether the user is an athlete")
    training_level: Optional[Literal["light", "casual", "intense"]] = Field(
        None,
        description="Training intensity level for athletes",
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_training_level(self):
        if not self.is_athlete and self.training_level is not None:
            raise ValueError("training_level must be null when is_athlete is false")
        if self.is_athlete and self.training_level is None:
            raise ValueError("training_level is required when is_athlete is true")
        return self


class UserPreferenceUpdate(BaseModel):
    diet_codes: Optional[List[str]] = Field(None, description="List of diet codes, e.g. ['vegan','gluten_free']")
    allergen_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user is allergic to")
    disliked_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user dislikes")
    goal: Optional[str] = Field(None, description="Goal preference as any string")
    calorie_target: Optional[int] = Field(None, ge=0, description="Daily calorie target")
    is_athlete: Optional[bool] = Field(None, description="Whether the user is an athlete")
    training_level: Optional[Literal["light", "casual", "intense"]] = Field(
        None,
        description="Training intensity level for athletes",
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_training_level(self):
        if self.is_athlete is False and self.training_level is not None:
            raise ValueError("training_level must be null when is_athlete is false")
        if self.is_athlete is True and self.training_level is None:
            raise ValueError("training_level is required when is_athlete is true")
        return self


class UserPreferenceOut(BaseModel):
    id: int = Field(..., description="Unique identifier of the user preference")
    user_id: int = Field(..., description="User this preference belongs to")
    diet_codes: Optional[List[str]] = Field(None, description="List of diet codes, e.g. ['vegan','gluten_free']")
    allergen_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user is allergic to")
    disliked_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user dislikes")
    goal: Optional[str] = Field(None, description="Goal preference as any string")
    calorie_target: Optional[int] = Field(None, ge=0, description="Daily calorie target")
    is_athlete: bool = Field(..., description="Whether the user is an athlete")
    training_level: Optional[Literal["light", "casual", "intense"]] = Field(
        None,
        description="Training intensity level for athletes",
    )
    created_at: datetime = Field(..., description="Timestamp when the preference was created")
    updated_at: datetime = Field(..., description="Timestamp when the preference was last updated")

    model_config = ConfigDict(from_attributes=True)
