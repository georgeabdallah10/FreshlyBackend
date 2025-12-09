from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from core.rate_limit import rate_limiter_with_user
from utils.cache import get_cache, invalidate_cache_pattern
from models.user import User
from models.grocery_list import GroceryList
from models.membership import FamilyMembership
from schemas.grocery_list import (
    GroceryListCreate,
    GroceryListUpdate,
    GroceryListOut,
    GroceryListItemCreate,
    GroceryListItemUpdate,
    GroceryListItemOut,
    AddFromRecipeRequest,
    AddFromRecipeResponse,
    SyncWithPantryResponse,
    RebuildFromMealPlanResponse,
    MarkPurchasedResponse,
    NormalizeIngredientRequest,
    NormalizedIngredientOut,
    MissingIngredient,
    RemainingItem,
)
from crud.grocery_lists import (
    list_grocery_lists,
    get_grocery_list,
    create_grocery_list,
    update_grocery_list,
    delete_grocery_list,
    get_grocery_list_item,
    create_grocery_list_item,
    update_grocery_list_item,
    delete_grocery_list_item,
    clear_checked_items,
)
from services.grocery_list_service import grocery_list_service
from services.ingredient_normalization_service import ingredient_normalization_service

router = APIRouter(prefix="/grocery-lists", tags=["grocery_lists"])


class ErrorOut(BaseModel):
    detail: str


# ===== Helper Functions =====

def _ensure_member(db: Session, user_id: int, family_id: int) -> None:
    """Verify user is member of family"""
    m = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.user_id == user_id,
            FamilyMembership.family_id == family_id
        )
        .first()
    )
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this family")


def _ensure_list_access(
    db: Session,
    grocery_list,
    user_id: int
) -> None:
    """Verify user has access to grocery list"""
    if not grocery_list_service.validate_list_access(db, grocery_list, user_id):
        raise HTTPException(status_code=403, detail="Access denied to this list")


def _ensure_list_creator(
    grocery_list: GroceryList,
    user_id: int
) -> None:
    """
    Verify user is the list creator (required for pantry sync).

    For personal lists: owner is the creator
    For family lists: check created_by_user_id field
    """
    # Personal list: creator is owner
    if grocery_list.owner_user_id:
        if grocery_list.owner_user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only the list owner can sync with pantry"
            )
        return

    # Family list: check created_by_user_id
    if grocery_list.created_by_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the list creator can sync with pantry"
        )


def _add_no_cache_headers(response: Response) -> None:
    """Add Cache-Control: no-store header to response"""
    response.headers["Cache-Control"] = "no-store"


def _build_cache_key(scope: str, scope_id: int) -> str:
    """Build cache key for grocery lists"""
    return f"grocery_lists:{scope}:{scope_id}"


# ===== GroceryList Endpoints =====

@router.get(
    "/family/{family_id}",
    response_model=list[GroceryListOut],
    responses={403: {"model": ErrorOut}},
)
async def list_family_lists(
    request: Request,
    response: Response,
    family_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-read")),
):
    """List all grocery lists for a family"""
    _ensure_member(db, current_user.id, family_id)
    _add_no_cache_headers(response)

    # Fetch from DB (no caching for grocery lists)
    lists = list_grocery_lists(db, family_id=family_id, status=status)

    return [GroceryListOut.from_orm_with_scope(l) for l in lists]


@router.get(
    "/me",
    response_model=list[GroceryListOut],
)
async def list_my_lists(
    request: Request,
    response: Response,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-read")),
):
    """List all personal grocery lists for current user"""
    _add_no_cache_headers(response)

    # Fetch from DB (no caching for grocery lists)
    lists = list_grocery_lists(db, owner_user_id=current_user.id, status=status)

    return [GroceryListOut.from_orm_with_scope(l) for l in lists]


@router.get(
    "/{list_id}",
    response_model=GroceryListOut,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def get_one_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-read")),
):
    """Get single grocery list with items"""
    g = get_grocery_list(db, list_id, load_items=True)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_list_access(db, g, current_user.id)

    return GroceryListOut.from_orm_with_scope(g)


@router.post(
    "",
    response_model=GroceryListOut,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorOut}},
)
async def create_one_list(
    data: GroceryListCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Create new grocery list"""
    _add_no_cache_headers(response)

    # Set owner_user_id from current_user for personal scope
    if data.scope == "personal":
        data.owner_user_id = current_user.id
        data.family_id = None
    elif data.scope == "family":
        _ensure_member(db, current_user.id, data.family_id)
        data.owner_user_id = None

    created = create_grocery_list(
        db,
        family_id=data.family_id,
        owner_user_id=data.owner_user_id,
        created_by_user_id=current_user.id,  # Always track who created the list
        title=data.title,
        status=data.status,
        meal_plan_id=data.meal_plan_id,
    )

    return GroceryListOut.from_orm_with_scope(created)


@router.patch(
    "/{list_id}",
    response_model=GroceryListOut,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def update_one_list(
    list_id: int,
    data: GroceryListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Update grocery list"""
    g = get_grocery_list(db, list_id)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_list_access(db, g, current_user.id)

    updated = update_grocery_list(
        db, g,
        title=data.title,
        status=data.status,
        meal_plan_id=data.meal_plan_id,
    )

    # Invalidate cache
    if updated.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{updated.family_id}")
    if updated.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{updated.owner_user_id}")

    return GroceryListOut.from_orm_with_scope(updated)


@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def delete_one_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Delete grocery list"""
    g = get_grocery_list(db, list_id)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_list_access(db, g, current_user.id)

    # Store IDs for cache invalidation
    family_id = g.family_id
    owner_user_id = g.owner_user_id

    delete_grocery_list(db, g)

    # Invalidate cache
    if family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{family_id}")
    if owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{owner_user_id}")

    return None


# ===== GroceryListItem Endpoints =====

@router.post(
    "/{list_id}/items",
    response_model=GroceryListItemOut,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def create_item(
    list_id: int,
    data: GroceryListItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Add item to grocery list"""
    g = get_grocery_list(db, list_id)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_list_access(db, g, current_user.id)

    item = create_grocery_list_item(
        db,
        grocery_list_id=list_id,
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        unit_id=data.unit_id,
        checked=data.checked,
        note=data.note,
    )

    # Invalidate cache
    if g.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{g.family_id}")
    if g.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{g.owner_user_id}")

    return GroceryListItemOut.model_validate(item, from_attributes=True)


@router.patch(
    "/items/{item_id}",
    response_model=GroceryListItemOut,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def update_item(
    item_id: int,
    data: GroceryListItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Update grocery list item"""
    item = get_grocery_list_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    g = get_grocery_list(db, item.grocery_list_id)
    _ensure_list_access(db, g, current_user.id)

    updated_item = update_grocery_list_item(
        db, item,
        quantity=data.quantity,
        unit_id=data.unit_id,
        checked=data.checked,
        note=data.note,
    )

    # Invalidate cache
    if g.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{g.family_id}")
    if g.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{g.owner_user_id}")

    return GroceryListItemOut.model_validate(updated_item, from_attributes=True)


@router.post(
    "/items/{item_id}/check",
    response_model=GroceryListItemOut,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def toggle_item_check(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Toggle item checked status"""
    item = get_grocery_list_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    g = get_grocery_list(db, item.grocery_list_id)
    _ensure_list_access(db, g, current_user.id)

    # Toggle checked status
    updated_item = update_grocery_list_item(
        db, item,
        checked=not item.checked,
    )

    # Invalidate cache
    if g.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{g.family_id}")
    if g.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{g.owner_user_id}")

    return GroceryListItemOut.model_validate(updated_item, from_attributes=True)


@router.post(
    "/items/{item_id}/mark-purchased",
    response_model=MarkPurchasedResponse,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def mark_item_purchased(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """
    Mark a grocery list item as purchased.

    This endpoint:
    1. Sets is_purchased = True on the grocery item
    2. Adds the canonical quantity to the user's pantry
    3. Returns the updated item and pantry information
    """
    try:
        grocery_item, pantry_item = grocery_list_service.mark_item_purchased(
            db,
            grocery_list_item_id=item_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)

    # Invalidate caches
    g = get_grocery_list(db, grocery_item.grocery_list_id)
    if g:
        if g.family_id:
            await invalidate_cache_pattern(f"grocery_lists:family:{g.family_id}")
            await invalidate_cache_pattern(f"pantry:family:{g.family_id}")
        if g.owner_user_id:
            await invalidate_cache_pattern(f"grocery_lists:user:{g.owner_user_id}")
            await invalidate_cache_pattern(f"pantry:user:{g.owner_user_id}")

    # Build response
    item_out = GroceryListItemOut(
        id=grocery_item.id,
        grocery_list_id=grocery_item.grocery_list_id,
        ingredient_id=grocery_item.ingredient_id,
        ingredient_name=grocery_item.ingredient.name if grocery_item.ingredient else None,
        quantity=grocery_item.quantity,
        unit_id=grocery_item.unit_id,
        unit_code=grocery_item.unit.code if grocery_item.unit else None,
        checked=grocery_item.checked,
        note=grocery_item.note,
        is_purchased=grocery_item.is_purchased,
        is_manual=grocery_item.is_manual,
        canonical_quantity_needed=grocery_item.canonical_quantity_needed,
        canonical_unit=grocery_item.canonical_unit,
        source_meal_plan_id=grocery_item.source_meal_plan_id,
    )

    return MarkPurchasedResponse(
        grocery_item=item_out,
        pantry_quantity_added=grocery_item.canonical_quantity_needed,
        pantry_unit=grocery_item.canonical_unit,
        message=f"Item marked as purchased and added to pantry",
    )


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Delete grocery list item"""
    item = get_grocery_list_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    g = get_grocery_list(db, item.grocery_list_id)
    _ensure_list_access(db, g, current_user.id)

    # Store IDs for cache invalidation
    family_id = g.family_id
    owner_user_id = g.owner_user_id

    delete_grocery_list_item(db, item)

    # Invalidate cache
    if family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{family_id}")
    if owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{owner_user_id}")

    return None


@router.delete(
    "/{list_id}/items/checked",
    status_code=status.HTTP_200_OK,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def clear_checked(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Clear all checked items from list"""
    g = get_grocery_list(db, list_id)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_list_access(db, g, current_user.id)

    count = clear_checked_items(db, list_id)

    # Invalidate cache
    if g.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{g.family_id}")
    if g.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{g.owner_user_id}")

    return {"items_removed": count, "message": f"Cleared {count} checked items"}


# ===== Recipe Integration Endpoints =====

@router.post(
    "/add-from-recipe",
    response_model=AddFromRecipeResponse,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def add_from_recipe(
    data: AddFromRecipeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Add recipe ingredients to grocery list"""
    # Validate access to existing list or family
    if data.list_id:
        g = get_grocery_list(db, data.list_id)
        if not g:
            raise HTTPException(status_code=404, detail="List not found")
        _ensure_list_access(db, g, current_user.id)

        family_id = g.family_id
        owner_user_id = g.owner_user_id
    else:
        # Creating new list
        if data.scope == "family":
            _ensure_member(db, current_user.id, data.family_id)
            family_id = data.family_id
            owner_user_id = None
        else:
            family_id = None
            owner_user_id = current_user.id

    # Add meal to list
    try:
        grocery_list, items_added = grocery_list_service.add_meal_to_list(
            db,
            meal_id=data.meal_id,
            list_id=data.list_id,
            family_id=family_id,
            owner_user_id=owner_user_id,
            title=data.title,
            servings_multiplier=data.servings_multiplier,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Invalidate cache
    if grocery_list.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{grocery_list.family_id}")
    if grocery_list.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{grocery_list.owner_user_id}")

    # Build response with missing ingredients
    missing = []
    for item in grocery_list.items:
        if not item.checked:  # Only include unchecked (missing) items
            missing.append(MissingIngredient(
                ingredient_id=item.ingredient_id,
                ingredient_name=item.ingredient.name if item.ingredient else "",
                quantity=item.quantity,
                unit_code=item.unit.code if item.unit else None,
                note=item.note,
            ))

    return AddFromRecipeResponse(
        grocery_list=GroceryListOut.from_orm_with_scope(grocery_list),
        items_added=items_added,
        missing_ingredients=missing,
        message=f"Added {items_added} ingredients to grocery list",
    )


@router.post(
    "/{list_id}/sync-pantry",
    response_model=SyncWithPantryResponse,
    responses={
        403: {"model": ErrorOut, "description": "Only list creator can sync with pantry"},
        404: {"model": ErrorOut},
    },
)
async def sync_with_pantry(
    list_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """
    Sync grocery list with current pantry inventory (creator only).

    This endpoint:
    1. Gets the full grocery list with each item's quantity and unit
    2. Normalizes units for each grocery item to canonical units
    3. Gets pantry items (family pantry if user is in family, else personal)
    4. Normalizes pantry item units to canonical units
    5. Calculates what's remaining to buy for each item
    6. Removes items fully covered by pantry, reduces partially covered items
    7. Returns items_removed, items_updated, and remaining_items

    Only the list creator can perform this operation.
    """
    _add_no_cache_headers(response)

    g = get_grocery_list(db, list_id, load_items=True)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    # Access check (view permission)
    _ensure_list_access(db, g, current_user.id)

    # Creator check (sync permission) - only creator can sync pantry
    _ensure_list_creator(g, current_user.id)

    try:
        items_removed, items_updated, remaining_items_data, updated_list = grocery_list_service.sync_list_with_pantry(
            db, g
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Invalidate caches
    if g.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{g.family_id}")
    if g.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{g.owner_user_id}")

    # Build remaining items list
    remaining_items = [
        RemainingItem(
            ingredient_id=item["ingredient_id"],
            ingredient_name=item["ingredient_name"],
            quantity=item.get("quantity"),
            unit_code=item.get("unit_code"),
            canonical_quantity=item.get("canonical_quantity"),
            canonical_unit=item.get("canonical_unit"),
            note=item.get("note"),
        )
        for item in remaining_items_data
    ]

    return SyncWithPantryResponse(
        items_removed=items_removed,
        items_updated=items_updated,
        remaining_items=remaining_items,
        message=f"Synced list: {items_removed} items removed, {items_updated} updated, {len(remaining_items)} items remaining",
    )


# ===== Meal Plan Integration Endpoints =====

@router.post(
    "/rebuild-from-meal-plan/{meal_plan_id}",
    response_model=RebuildFromMealPlanResponse,
    responses={
        403: {"model": ErrorOut, "description": "User not authorized to access this meal plan"},
        404: {"model": ErrorOut, "description": "Meal plan not found"},
    },
)
async def rebuild_from_meal_plan(
    meal_plan_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """
    Rebuild grocery list from meal plan using canonical unit calculations.

    This endpoint:
    1. Calculates total canonical ingredient requirements from all meals in the plan
    2. Compares against canonical pantry quantities
    3. Computes remaining quantities needed
    4. Creates grocery list items with both canonical and display units

    Only items where the user still needs to buy are included in the list.
    """
    _add_no_cache_headers(response)

    try:
        grocery_list = grocery_list_service.rebuild_grocery_list_from_meal_plan(
            db,
            meal_plan_id=meal_plan_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        # Check if it's a not found or authorization error
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)

    # Invalidate cache
    if grocery_list.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{grocery_list.family_id}")
    if grocery_list.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{grocery_list.owner_user_id}")

    items_count = len(grocery_list.items) if grocery_list.items else 0

    return RebuildFromMealPlanResponse(
        grocery_list=GroceryListOut.from_orm_with_scope(grocery_list),
        items_count=items_count,
        message=f"Rebuilt grocery list with {items_count} items from meal plan",
    )


@router.post(
    "/ingredients/normalize",
    response_model=NormalizedIngredientOut,
)
async def normalize_ingredient(
    data: NormalizeIngredientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("chat")),  # Use chat rate limit (AI-powered)
):
    """Normalize ingredient text using AI (on-demand feature)"""
    try:
        result = await ingredient_normalization_service.normalize_ingredient(
            data.raw_text
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingredient normalization failed: {str(e)}"
        )


# ===== Debug Endpoints =====

@router.get(
    "/debug/meal-plan/{meal_plan_id}",
    responses={
        403: {"model": ErrorOut, "description": "User not authorized to access this meal plan"},
        404: {"model": ErrorOut, "description": "Meal plan not found"},
    },
)
async def debug_meal_plan_requirements(
    meal_plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-read")),
):
    """
    Debug endpoint to inspect meal plan requirements and pantry availability.

    Returns detailed breakdown of:
    - Total ingredients needed from meal plan
    - Current pantry availability
    - Remaining to buy for each ingredient

    Useful for troubleshooting grocery list calculations.
    """
    try:
        debug_info = grocery_list_service.debug_meal_plan_requirements(
            db,
            meal_plan_id=meal_plan_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)

    return debug_info
