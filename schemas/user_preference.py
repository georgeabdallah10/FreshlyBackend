# schemas/user_preference.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime


class UserPreferenceCreate(BaseModel):
    diet_codes: List[str] = Field(..., description="List of diet codes, e.g. ['vegan','gluten_free']")
    allergen_ingredient_ids: List[int] = Field(..., description="Ingredient IDs the user is allergic to")
    disliked_ingredient_ids: List[int] = Field(..., description="Ingredient IDs the user dislikes")
    goal: str = Field(..., description="Goal preference as any string")
    calorie_target: int = Field(..., ge=0, description="Daily calorie target")

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceUpdate(BaseModel):
    diet_codes: Optional[List[str]] = Field(None, description="List of diet codes, e.g. ['vegan','gluten_free']")
    allergen_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user is allergic to")
    disliked_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user dislikes")
    goal: Optional[str] = Field(None, description="Goal preference as any string")
    calorie_target: Optional[int] = Field(None, ge=0, description="Daily calorie target")

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceOut(BaseModel):
    id: int = Field(..., description="Unique identifier of the user preference")
    user_id: int = Field(..., description="User this preference belongs to")
    diet_codes: Optional[List[str]] = Field(None, description="List of diet codes, e.g. ['vegan','gluten_free']")
    allergen_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user is allergic to")
    disliked_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user dislikes")
    goal: Optional[str] = Field(None, description="Goal preference as any string")
    calorie_target: Optional[int] = Field(None, ge=0, description="Daily calorie target")
    created_at: datetime = Field(..., description="Timestamp when the preference was created")
    updated_at: datetime = Field(..., description="Timestamp when the preference was last updated")

    model_config = ConfigDict(from_attributes=True)