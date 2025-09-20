# schemas/pantry_item.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class PantryItemUpsert(BaseModel):
    """Create or replace (idempotent) by (family_id, ingredient_id, unit_id)."""
    family_id: int = Field(..., description="Family that owns this pantry item")
    ingredient_id: int = Field(..., description="Ingredient reference")
    quantity: Optional[Decimal] = Field(
        None, ge=0, description="Quantity on hand (precision up to 3 decimals)"
    )
    unit_id: Optional[int] = Field(
        None, description="Unit for the quantity (e.g., g, ml, cup). Optional for count-based items"
    )
    expires_at: Optional[date] = Field(None, description="Optional expiration date")


class PantryItemUpdate(BaseModel):
    """Partial update for an existing pantry item."""
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit_id: Optional[int] = None
    expires_at: Optional[date] = None


class PantryItemOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    family_id: int
    ingredient_id: int
    quantity: Optional[Decimal] = None
    unit_id: Optional[int] = None
    expires_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime