# routers/grocery_lists.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from models.user import User
from models.membership import FamilyMembership
from schemas.grocery_list import GroceryListCreate, GroceryListUpdate, GroceryListOut
from crud.grocery_lists import (
    list_grocery_lists,
    get_grocery_list,
    create_grocery_list,
    update_grocery_list,
    delete_grocery_list,
)

router = APIRouter(prefix="/grocery-lists", tags=["grocery_lists"])


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
    response_model=list[GroceryListOut],
    responses={403: {"model": ErrorOut, "description": "Not a member"}},
)
def list_for_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_member(db, current_user.id, family_id)
    return list_grocery_lists(db, family_id=family_id)


@router.post(
    "",
    response_model=GroceryListOut,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorOut, "description": "Not a member"}},
)
def create_one_list(
    data: GroceryListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_member(db, current_user.id, data.family_id)
    return create_grocery_list(
        db,
        family_id=data.family_id,
        title=data.title,
        status=data.status,
        meal_plan_id=data.meal_plan_id,
    )


@router.patch(
    "/{list_id}",
    response_model=GroceryListOut,
    responses={
        403: {"model": ErrorOut, "description": "Not a member"},
        404: {"model": ErrorOut, "description": "List not found"},
    },
)
def update_one_list(
    list_id: int,
    data: GroceryListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = get_grocery_list(db, list_id)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_member(db, current_user.id, g.family_id)
    return update_grocery_list(
        db,
        g,
        title=data.title,
        status=data.status,
        meal_plan_id=data.meal_plan_id,
    )


@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorOut, "description": "Not a member"},
        404: {"model": ErrorOut, "description": "List not found"},
    },
)
def delete_one_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = get_grocery_list(db, list_id)
    if not g:
        raise HTTPException(status_code=404, detail="List not found")

    _ensure_member(db, current_user.id, g.family_id)
    delete_grocery_list(db, g)
    return None