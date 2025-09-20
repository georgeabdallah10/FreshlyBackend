# schemas/user_preference.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserPreferenceCreate(BaseModel):
    user_id: int = Field(..., description="User this preference belongs to")
    diet_codes: Optional[List[str]] = Field(None, description="List of diet codes, e.g. ['vegan','gluten_free']")
    allergen_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user is allergic to")
    disliked_ingredient_ids: Optional[List[int]] = Field(None, description="Ingredient IDs the user dislikes")
    goal: Optional[str] = Field(None, description="weight_loss | muscle_gain | maintenance | balanced")
    calorie_target: Optional[int] = Field(None, ge=0, description="Daily calorie target")


class UserPreferenceUpdate(BaseModel):
    diet_codes: Optional[List[str]] = None
    allergen_ingredient_ids: Optional[List[int]] = None
    disliked_ingredient_ids: Optional[List[int]] = None
    goal: Optional[str] = None
    calorie_target: Optional[int] = None


class UserPreferenceOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    diet_codes: Optional[List[str]] = None
    allergen_ingredient_ids: Optional[List[int]] = None
    disliked_ingredient_ids: Optional[List[int]] = None
    goal: Optional[str] = None
    calorie_target: Optional[int] = None
    created_at: datetime
    updated_at: datetime