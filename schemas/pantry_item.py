# schemas/pantry_item.py
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import datetime, date
from decimal import Decimal


class PantryItemCreate(BaseModel):
    """Schema for creating a new pantry item.
    ingredient_id is optional and will be auto-created if not provided."""
    model_config = {"populate_by_name": True}

    family_id: Optional[int] = None
    scope: Optional[Literal["personal", "family"]] = None
    category: str | None = None   # <— add

    ingredient_id: Optional[int] = None
    name: Optional[str] = Field(None, alias="ingredient_name")
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = None
    expires_at: Optional[date] = None

    @model_validator(mode="before")
    def _normalize_scope_and_family(cls, data: dict):
        # Allow missing scope by inferring from family_id
        scope = data.get("scope")
        family_id = data.get("family_id")
        if scope is None:
            data["scope"] = "family" if family_id is not None else "personal"
            return data

        if scope == "personal" and family_id is not None:
            raise ValueError("For scope='personal', omit family_id.")
        if scope == "family" and family_id is None:
            raise ValueError("For scope='family', you must provide family_id.")
        if scope not in (None, "personal", "family"):
            raise ValueError("scope must be either 'personal' or 'family'.")
        return data


class PantryItemUpsert(BaseModel):
    """Create or replace (idempotent) by (family_id, ingredient_id, unit_id)."""
    model_config = {"populate_by_name": True}
    family_id: int = Field(..., description="Family that owns this pantry item")
    ingredient_id: int = Field(..., description="Ingredient reference")
    quantity: Optional[Decimal] = Field(
        None, ge=0, description="Quantity on hand (precision up to 3 decimals)"
    )
    unit: Optional[str] = None
    expires_at: Optional[date] = Field(None, description="Optional expiration date")
    category: str | None = None   # <— add


class PantryItemUpdate(BaseModel):
    """Partial update for an existing pantry item."""
    model_config = {"populate_by_name": True}
    name: Optional[str] = Field(None, alias="ingredient_name")
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit: Optional[str] = None    
    expires_at: Optional[date] = None
    category: str | None = None   # <— add


class PantryItemOut(BaseModel):
    model_config = {"from_attributes": True, "populate_by_name": True}

    id: int
    family_id: Optional[int]
    owner_user_id: Optional[int]
    scope: Literal["personal", "family"]
    category: str | None = None   # <— add
    ingredient_name: str | None = None
    image_url: str | None = None  # Generated image URL

    ingredient_id: int
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    expires_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    @classmethod
    def from_orm(cls, obj):
        scope = "family" if obj.family_id is not None else "personal"
        d = super().model_validate(obj, from_attributes=True)
        d.scope = scope
        return d