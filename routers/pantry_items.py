# routers/pantry_items.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
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
    return list_pantry_items(db, family_id=family_id)


@router.post(
    "",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorOut, "description": "Not a member"}},
)
def create_one_item(
    data: PantryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_member(db, current_user.id, data.family_id)
    return create_pantry_item(
        db,
        family_id=data.family_id,
        ingredient_id=data.ingredient_id,
        quantity=data.quantity,
        unit_id=data.unit_id,
        expires_at=data.expires_at,
    )


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

    _ensure_member(db, current_user.id, item.family_id)
    return update_pantry_item(
        db, item, quantity=data.quantity, unit_id=data.unit_id, expires_at=data.expires_at
    )


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

    _ensure_member(db, current_user.id, item.family_id)
    delete_pantry_item(db, item)
    return None