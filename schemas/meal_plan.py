# schemas/meal_plan.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class MealPlanCreate(BaseModel):
    family_id: int = Field(..., description="Family this meal plan belongs to")
    title: Optional[str] = Field(None, max_length=200)
    week_start: date = Field(..., description="Start of the meal plan week")
    week_end: Optional[date] = Field(None, description="End of the meal plan week")


class MealPlanUpdate(BaseModel):
    title: Optional[str] = None
    week_start: Optional[date] = None
    week_end: Optional[date] = None


class MealPlanOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    family_id: int
    title: Optional[str] = None
    week_start: date
    week_end: Optional[date] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime


# ------------------------------
# MealSlot Schemas
# ------------------------------
class MealSlotCreate(BaseModel):
    meal_plan_id: int = Field(..., description="Meal plan this slot belongs to")
    day: int = Field(..., ge=0, le=6, description="Day of the week (0–6)")
    slot: str = Field(..., description="breakfast | lunch | dinner | snack")
    servings: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class MealSlotUpdate(BaseModel):
    servings: Optional[int] = None
    notes: Optional[str] = None


class MealSlotOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    meal_plan_id: int
    day: int
    slot: str
    servings: Optional[int] = None
    notes: Optional[str] = None


# ------------------------------
# MealSlotRecipe Schemas
# ------------------------------
class MealSlotRecipeCreate(BaseModel):
    meal_slot_id: int = Field(..., description="Slot this recipe belongs to")
    recipe_id: int = Field(..., description="Recipe reference")
    portions: Optional[int] = Field(None, ge=1)


class MealSlotRecipeUpdate(BaseModel):
    portions: Optional[int] = None


class MealSlotRecipeOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    meal_slot_id: int
    recipe_id: int
    portions: Optional[int] = None