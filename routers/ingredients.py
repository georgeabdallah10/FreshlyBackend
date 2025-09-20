# routers/ingredients.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user  # keep if you want to protect writes
from schemas.ingredient import IngredientCreate, IngredientUpdate, IngredientOut
from crud.ingredients import (
    list_ingredients,
    get_ingredient,
    get_ingredient_by_name,
    create_ingredient,
    update_ingredient,
    delete_ingredient,
)

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


class ErrorOut(BaseModel):
    detail: str


@router.get(
    "",
    response_model=list[IngredientOut],
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}},
)
def list_all_ingredients(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),  # remove if you want this public
):
    return list_ingredients(db)


@router.get(
    "/{ingredient_id}",
    response_model=IngredientOut,
    responses={404: {"model": ErrorOut, "description": "Ingredient not found"}},
)
def get_one_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ing = get_ingredient(db, ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ing


@router.post(
    "",
    response_model=IngredientOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorOut, "description": "Ingredient name already exists"}},
)
def create_one_ingredient(
    data: IngredientCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    # prevent duplicate names with a clean 409
    if get_ingredient_by_name(db, data.name):
        raise HTTPException(status_code=409, detail="Ingredient name already exists")
    try:
        return create_ingredient(db, name=data.name, category=data.category)
    except Exception:
        # Unique violation fallback
        raise HTTPException(status_code=409, detail="Ingredient name already exists")


@router.patch(
    "/{ingredient_id}",
    response_model=IngredientOut,
    responses={
        404: {"model": ErrorOut, "description": "Ingredient not found"},
        409: {"model": ErrorOut, "description": "Ingredient name already exists"},
    },
)
def update_one_ingredient(
    ingredient_id: int,
    data: IngredientUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    ing = get_ingredient(db, ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    # If changing name, check uniqueness
    if data.name is not None:
        existing = get_ingredient_by_name(db, data.name)
        if existing and existing.id != ing.id:
            raise HTTPException(status_code=409, detail="Ingredient name already exists")

    try:
        return update_ingredient(db, ing, name=data.name, category=data.category)
    except Exception:
        raise HTTPException(status_code=409, detail="Ingredient name already exists")


@router.delete(
    "/{ingredient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorOut, "description": "Ingredient not found"}},
)
def delete_one_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    ing = get_ingredient(db, ingredient_id)
    if not ing:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    delete_ingredient(db, ing)
    return None