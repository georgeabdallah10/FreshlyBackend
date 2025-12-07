from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from core.rate_limit import rate_limiter_with_user
from core.cache_headers import cache_control
from utils.cache import get_cache, invalidate_cache_pattern
from models.user import User
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
    NormalizeIngredientRequest,
    NormalizedIngredientOut,
    MissingIngredient,
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


def _build_cache_key(scope: str, scope_id: int) -> str:
    """Build cache key for grocery lists"""
    return f"grocery_lists:{scope}:{scope_id}"


# ===== GroceryList Endpoints =====

@router.get(
    "/family/{family_id}",
    response_model=list[GroceryListOut],
    responses={403: {"model": ErrorOut}},
)
@cache_control(max_age=60, private=True)
async def list_family_lists(
    request: Request,
    family_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-read")),
):
    """List all grocery lists for a family"""
    _ensure_member(db, current_user.id, family_id)

    # Try cache first
    cache = get_cache()
    cache_key = _build_cache_key("family", family_id)
    cached_lists = await cache.get(cache_key)

    if cached_lists and not status:
        return [GroceryListOut.from_orm_with_scope(l) for l in cached_lists]

    # Cache miss - fetch from DB
    lists = list_grocery_lists(db, family_id=family_id, status=status)

    # Cache for 60 seconds (if no status filter)
    if not status:
        await cache.set(cache_key, lists, ttl=60)

    return [GroceryListOut.from_orm_with_scope(l) for l in lists]


@router.get(
    "/me",
    response_model=list[GroceryListOut],
)
@cache_control(max_age=60, private=True)
async def list_my_lists(
    request: Request,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-read")),
):
    """List all personal grocery lists for current user"""
    # Try cache first
    cache = get_cache()
    cache_key = _build_cache_key("user", current_user.id)
    cached_lists = await cache.get(cache_key)

    if cached_lists and not status:
        return [GroceryListOut.from_orm_with_scope(l) for l in cached_lists]

    # Cache miss
    lists = list_grocery_lists(db, owner_user_id=current_user.id, status=status)

    if not status:
        await cache.set(cache_key, lists, ttl=60)

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Create new grocery list"""
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
        title=data.title,
        status=data.status,
        meal_plan_id=data.meal_plan_id,
    )

    # Invalidate cache
    if created.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{created.family_id}")
    if created.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{created.owner_user_id}")

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
    "/{list_id}/sync-with-pantry",
    response_model=SyncWithPantryResponse,
    responses={403: {"model": ErrorOut}, 404: {"model": ErrorOut}},
)
async def sync_with_pantry(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("grocery-write")),
):
    """Sync grocery list with current pantry inventory"""
    g = get_grocery_list(db, list_id)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_list_access(db, g, current_user.id)

    try:
        items_removed, items_updated = grocery_list_service.sync_list_with_pantry(
            db, list_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Invalidate cache
    if g.family_id:
        await invalidate_cache_pattern(f"grocery_lists:family:{g.family_id}")
    if g.owner_user_id:
        await invalidate_cache_pattern(f"grocery_lists:user:{g.owner_user_id}")

    return SyncWithPantryResponse(
        items_removed=items_removed,
        items_updated=items_updated,
        message=f"Synced list: {items_removed} items removed, {items_updated} updated",
    )


# ===== AI Ingredient Normalization Endpoint =====

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
