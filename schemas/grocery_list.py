from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal


# ===== GroceryList Schemas =====

class GroceryListCreate(BaseModel):
    """Create grocery list with dual-scope support"""

    family_id: Optional[int] = Field(None, description="Family scope")
    owner_user_id: Optional[int] = Field(None, description="Personal scope (auto-set from auth)")
    scope: Literal["family", "personal"] = Field(..., description="Scope selector")

    meal_plan_id: Optional[int] = Field(None, description="Optional meal plan reference")
    title: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field("draft", description="draft | finalized | purchased")

    @model_validator(mode="before")
    def validate_scope(cls, data: dict):
        """Validate XOR constraint on scope"""
        scope = data.get("scope")
        family_id = data.get("family_id")
        owner_user_id = data.get("owner_user_id")

        if scope == "family":
            if not family_id:
                raise ValueError("family_id required for family scope")
            if owner_user_id:
                raise ValueError("Cannot set owner_user_id for family scope")
        elif scope == "personal":
            if family_id:
                raise ValueError("Cannot set family_id for personal scope")
            # owner_user_id will be set by router from current_user
        else:
            raise ValueError("scope must be 'family' or 'personal'")

        return data


class GroceryListUpdate(BaseModel):
    """Update grocery list fields"""
    title: Optional[str] = None
    status: Optional[str] = None
    meal_plan_id: Optional[int] = None


class GroceryListItemSummary(BaseModel):
    """Embedded item summary in list response"""
    model_config = {"from_attributes": True}

    id: int
    ingredient_id: int
    ingredient_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_code: Optional[str] = None
    checked: bool
    note: Optional[str] = None
    # Phase 3 fields
    is_purchased: Optional[bool] = False
    is_manual: Optional[bool] = False
    canonical_quantity_needed: Optional[Decimal] = None
    canonical_unit: Optional[str] = None


class GroceryListOut(BaseModel):
    """Grocery list with items"""
    model_config = {"from_attributes": True}

    id: int
    family_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    scope: Literal["family", "personal"]
    meal_plan_id: Optional[int] = None
    title: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    items: list[GroceryListItemSummary] = []

    @classmethod
    def from_orm_with_scope(cls, obj):
        """Add scope field based on family_id/owner_user_id"""
        data = {
            "id": obj.id,
            "family_id": obj.family_id,
            "owner_user_id": obj.owner_user_id,
            "created_by_user_id": obj.created_by_user_id,
            "scope": "family" if obj.family_id else "personal",
            "meal_plan_id": obj.meal_plan_id,
            "title": obj.title,
            "status": obj.status,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "items": []
        }

        # Populate ingredient names and unit codes
        if obj.items:
            items_with_names = []
            for item in obj.items:
                item_dict = {
                    "id": item.id,
                    "ingredient_id": item.ingredient_id,
                    "ingredient_name": item.ingredient.name if item.ingredient else None,
                    "quantity": item.quantity,
                    "unit_code": item.unit.code if item.unit else None,
                    "checked": item.checked,
                    "note": item.note,
                    # Phase 3 fields
                    "is_purchased": getattr(item, 'is_purchased', False),
                    "is_manual": getattr(item, 'is_manual', False),
                    "canonical_quantity_needed": getattr(item, 'canonical_quantity_needed', None),
                    "canonical_unit": getattr(item, 'canonical_unit', None),
                }
                items_with_names.append(GroceryListItemSummary(**item_dict))
            data["items"] = items_with_names

        return cls(**data)


# ===== GroceryListItem Schemas =====

class GroceryListItemCreate(BaseModel):
    """Create single grocery list item"""
    ingredient_id: int = Field(..., description="Ingredient reference")
    quantity: Optional[Decimal] = Field(None, ge=0)
    unit_id: Optional[int] = Field(None)
    checked: Optional[bool] = Field(False)
    note: Optional[str] = None


class GroceryListItemUpdate(BaseModel):
    """Update grocery list item"""
    quantity: Optional[Decimal] = None
    unit_id: Optional[int] = None
    checked: Optional[bool] = None
    note: Optional[str] = None


class GroceryListItemOut(BaseModel):
    """Single grocery list item response"""
    model_config = {"from_attributes": True}

    id: int
    grocery_list_id: int
    ingredient_id: int
    ingredient_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    checked: bool
    note: Optional[str] = None
    # Phase 3 fields
    is_purchased: Optional[bool] = False
    is_manual: Optional[bool] = False
    canonical_quantity_needed: Optional[Decimal] = None
    canonical_unit: Optional[str] = None
    source_meal_plan_id: Optional[int] = None


class MarkPurchasedResponse(BaseModel):
    """Response after marking a grocery item as purchased"""
    grocery_item: GroceryListItemOut
    pantry_quantity_added: Optional[Decimal] = None
    pantry_unit: Optional[str] = None
    message: str


# ===== Recipe Integration Schemas =====

class AddFromRecipeRequest(BaseModel):
    """Request to add meal ingredients to grocery list"""
    meal_id: int = Field(..., description="Meal to add", alias="recipe_id")  # Accept both meal_id and recipe_id from frontend
    list_id: Optional[int] = Field(None, description="Existing list (or create new)")

    # For new list
    scope: Optional[Literal["family", "personal"]] = Field(None, description="Scope for new list")
    family_id: Optional[int] = Field(None, description="Family scope for new list")
    title: Optional[str] = Field(None, description="Title for new list")

    # Recipe scaling
    servings_multiplier: Optional[float] = Field(1.0, gt=0, description="Scale recipe quantities")

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    def validate_list_or_scope(cls, data: dict):
        """Validate either list_id or scope is provided"""
        if not data.get("list_id"):
            # Creating new list - need scope
            if not data.get("scope"):
                raise ValueError("scope required when creating new list")
            if data["scope"] == "family" and not data.get("family_id"):
                raise ValueError("family_id required for family scope")
        return data


class MissingIngredient(BaseModel):
    """Missing ingredient details"""
    ingredient_id: int
    ingredient_name: str
    quantity: Optional[Decimal]
    unit_code: Optional[str]
    note: Optional[str]
    source: Literal["personal_pantry", "family_pantry", "not_in_pantry"] = "not_in_pantry"


class AddFromRecipeResponse(BaseModel):
    """Response after adding recipe to list"""
    grocery_list: GroceryListOut
    items_added: int
    missing_ingredients: list[MissingIngredient]
    message: str


class RemainingItem(BaseModel):
    """Item remaining to be purchased after sync"""
    ingredient_id: int
    ingredient_name: str
    quantity: Optional[Decimal] = None
    unit_code: Optional[str] = None
    canonical_quantity: Optional[Decimal] = None
    canonical_unit: Optional[str] = None
    note: Optional[str] = None  # Display text for items without parsed quantities


class SyncWithPantryResponse(BaseModel):
    """Response after syncing list with pantry"""
    items_removed: int
    items_updated: int
    remaining_items: list[RemainingItem]
    message: str


class RebuildFromMealPlanResponse(BaseModel):
    """Response after rebuilding grocery list from meal plan"""
    grocery_list: GroceryListOut
    items_count: int
    message: str


# ===== Ingredient Normalization Schemas =====

class NormalizeIngredientRequest(BaseModel):
    """Request to normalize ingredient text"""
    raw_text: str = Field(..., min_length=1, max_length=500)


class NormalizedIngredientOut(BaseModel):
    """Normalized ingredient result"""
    normalized_name: str
    category: Optional[str]
    quantity: Optional[float]
    unit: Optional[str]
    confidence: float
    notes: Optional[str]
