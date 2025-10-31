# routers/pantry_items.py
from fastapi import APIRouter, Depends, HTTPException, status, Path, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from models.user import User
from models.membership import FamilyMembership
from schemas.pantry_item import PantryItemCreate, PantryItemUpdate, PantryItemOut
from crud.pantry_items import (
    list_pantry_items,
    get_pantry_item,
    create_pantry_item,
    update_pantry_item,
    delete_pantry_item,
    create_or_get_ingredient
)
from crud.ingredients import get_ingredient
from services.pantry_image_service import pantry_image_service

# at top of routers/pantry_items.py
from typing import List
from models.pantry_item import PantryItem
from schemas.pantry_item import PantryItemOut  # whatever your output schema is called

def _to_out(item: PantryItem) -> PantryItemOut:
    """Map ORM -> API schema and inject `scope`."""
    scope = "personal" if item.owner_user_id is not None else "family"
    return PantryItemOut(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient.name if getattr(item, "ingredient", None) else None,
        quantity=item.quantity,
        unit=item.unit,
        expires_at=item.expires_at,
        category=item.category,
        family_id=item.family_id,
        owner_user_id=item.owner_user_id,
        scope=scope,
        image_url=item.image_url,  # Include generated image URL
        created_at=item.created_at,
        updated_at=item.updated_at,
    )

router = APIRouter(prefix="/pantry-items", tags=["pantry_items"])


class ErrorOut(BaseModel):
    detail: str


# ---- helpers ----
def _ensure_member(db: Session, user_id: int, family_id: int) -> None:
    m = (
        db.query(FamilyMembership)
        .filter(FamilyMembership.user_id == user_id, FamilyMembership.family_id == family_id)
        .first()
    )
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this family")


# ---- endpoints ----
@router.get(
    "/family/{family_id}",
    response_model=list[PantryItemOut],
    responses={403: {"model": ErrorOut, "description": "Not a member"}},
)
def list_for_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_member(db, current_user.id, family_id)
    items = list_pantry_items(db, family_id=family_id)
    return [_to_out(i) for i in items]


@router.post(
    "",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorOut, "description": "Not a member"}},
)
async def create_one_item(
    data: PantryItemCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve ingredient: if no id is provided but a name is, create or fetch it
    ingredient_id = data.ingredient_id
    ingredient_name = data.name
    
    if ingredient_id is None and data.name:
        ing = create_or_get_ingredient(db, data.name)
        ingredient_id = ing.id
        ingredient_name = ing.name
    elif ingredient_id and not ingredient_name:
        # Get ingredient name from database
        from crud.ingredients import get_ingredient
        ing = get_ingredient(db, ingredient_id)
        if ing:
            ingredient_name = ing.name

    # Support both family and personal scopes
    if data.scope == "family":
        _ensure_member(db, current_user.id, data.family_id)
        created = create_pantry_item(
            db,
            family_id=data.family_id,
            ingredient_id=ingredient_id,
            quantity=data.quantity,
            unit=data.unit,
            expires_at=data.expires_at,
            category=data.category
        )
        
        # Schedule background image generation
        if ingredient_name:
            background_tasks.add_task(
                pantry_image_service.generate_image_background,
                db, current_user, created, ingredient_name
            )
        
        return _to_out(created)
        
    elif data.scope == "personal":
        created = create_pantry_item(
            db,
            owner_user_id=current_user.id,
            family_id=None,
            ingredient_id=ingredient_id,
            quantity=data.quantity,
            unit=data.unit,
            expires_at=data.expires_at,
            category=data.category
        )
        
        # Schedule background image generation
        if ingredient_name:
            background_tasks.add_task(
                pantry_image_service.generate_image_background,
                db, current_user, created, ingredient_name
            )
        
        return _to_out(created)
    else:
        raise HTTPException(status_code=400, detail="Invalid scope")

@router.patch(
    "/{item_id}",
    response_model=PantryItemOut,
    responses={
        403: {"model": ErrorOut, "description": "Not a member"},
        404: {"model": ErrorOut, "description": "Item not found"},
    },
)
def update_one_item(
    item_id: int,
    data: PantryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_pantry_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.family_id is not None:
        _ensure_member(db, current_user.id, item.family_id)
    elif item.owner_user_id is not None:
        if item.owner_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this item")
    else:
        raise HTTPException(status_code=403, detail="Not authorized to modify this item")
    updated_item = update_pantry_item(
        db, item, quantity=data.quantity, unit=data.unit, expires_at=data.expires_at ,category=data.category
    )
    return _to_out(updated_item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorOut, "description": "Not a member"},
        404: {"model": ErrorOut, "description": "Item not found"},
    },
)
def delete_one_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_pantry_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.family_id is not None:
        _ensure_member(db, current_user.id, item.family_id)
    elif item.owner_user_id is not None:
        if item.owner_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this item")
    else:
        raise HTTPException(status_code=403, detail="Not authorized to modify this item")
    delete_pantry_item(db, item)
    return None

@router.get(
    "/me",
    response_model=list[PantryItemOut],
)
def list_my_pantry(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items =  list_pantry_items(db, owner_user_id=current_user.id)
    return [_to_out(i) for i in items]

@router.post(
    "/me",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_my_pantry_item(
    data: PantryItemCreate,   # expects scope='personal' and no family_id
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.scope != "personal" or data.family_id is not None:
        raise HTTPException(400, "Use scope='personal' with no family_id for this endpoint")

    # Resolve ingredient: create or fetch by name when id is not provided
    ingredient_id = data.ingredient_id
    if ingredient_id is None and data.name:
        ing = create_or_get_ingredient(db, data.name)
        ingredient_id = ing.id

    item =  create_pantry_item(
        db,
        owner_user_id=current_user.id,
        family_id=None,
        ingredient_id=ingredient_id,
        quantity=data.quantity,
        unit=data.unit,
        expires_at=data.expires_at,
        category=data.category
    )
    return _to_out(item)