# routers/user_preferences.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from models.user import User
from schemas.user_preference import UserPreferenceCreate, UserPreferenceOut  # <-- FIXED
from crud.user_preferences import (
    get_user_preference,
    create_or_update_user_preference,
    delete_user_preference,
)

router = APIRouter(prefix="/preferences", tags=["user_preferences"])


class ErrorOut(BaseModel):
    detail: str


@router.get(
    "/me",
    response_model=UserPreferenceOut,
    responses={404: {"model": ErrorOut, "description": "Preferences not set"}},
)
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pref = get_user_preference(db, current_user.id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not set")
    return pref


@router.post(
    "/me",
    response_model=UserPreferenceOut,
    status_code=status.HTTP_201_CREATED,
)
def set_my_preferences(
    data: UserPreferenceCreate,  # <-- FIXED: use the defined schema
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pref = create_or_update_user_preference(
        db,
        current_user.id,
        diet_codes=data.diet_codes,
        allergen_ingredient_ids=data.allergen_ingredient_ids,
        disliked_ingredient_ids=data.disliked_ingredient_ids,
        goal=data.goal,
        calorie_target=data.calorie_target,
    )
    return pref


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorOut, "description": "Preferences not set"}},
)
def delete_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pref = get_user_preference(db, current_user.id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not set")
    delete_user_preference(db, pref)
    return None