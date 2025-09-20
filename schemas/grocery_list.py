# schemas/grocery_list.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ------------------------------
# GroceryList Schemas
# ------------------------------
class GroceryListCreate(BaseModel):
    family_id: int = Field(..., description="Family this grocery list belongs to")
    meal_plan_id: Optional[int] = Field(None, description="Optional meal plan reference")
    title: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(
        "draft", description="draft | finalized | purchased"
    )


class GroceryListUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class GroceryListOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    family_id: int
    meal_plan_id: Optional[int] = None
    title: Optional[str] = None
    status: str
    created_at: datetime


# ------------------------------
# GroceryListItem Schemas
# ------------------------------
class GroceryListItemCreate(BaseModel):
    grocery_list_id: int = Field(..., description="The grocery list this item belongs to")
    ingredient_id: int = Field(..., description="Ingredient reference")
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit_id: Optional[int] = Field(None)
    checked: Optional[bool] = Field(False, description="Whether this item is marked off")
    note: Optional[str] = None


class GroceryListItemUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    unit_id: Optional[int] = None
    checked: Optional[bool] = None
    note: Optional[str] = None


class GroceryListItemOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    grocery_list_id: int
    ingredient_id: int
    quantity: Optional[Decimal] = None
    unit_id: Optional[int] = None
    checked: bool
    note: Optional[str] = None