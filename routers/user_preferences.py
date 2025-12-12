# routers/user_preferences.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from models.user import User
from schemas.user_preference import (
    UserPreferenceCreate,
    UserPreferenceUpdate,
    UserPreferenceOut,
)
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
    """Get the current user's preferences."""
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
    data: UserPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or fully replace the current user's preferences."""
    try:
        pref = create_or_update_user_preference(
            db,
            current_user.id,
            # Basic body information
            age=data.age,
            gender=data.gender,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            # Dietary preferences (legacy)
            diet_codes=data.diet_codes,
            allergen_ingredient_ids=data.allergen_ingredient_ids,
            disliked_ingredient_ids=data.disliked_ingredient_ids,
            # Dietary preferences (new)
            diet_type=data.diet_type,
            food_allergies=data.food_allergies,
            # Goal & athlete
            goal=data.goal,
            is_athlete=data.is_athlete,
            training_level=data.training_level,
            # Nutrition targets
            calorie_target=data.calorie_target,
            protein_grams=data.protein_grams,
            carb_grams=data.carb_grams,
            fat_grams=data.fat_grams,
            protein_calories=data.protein_calories,
            carb_calories=data.carb_calories,
            fat_calories=data.fat_calories,
            # Safety range
            calorie_min=data.calorie_min,
            calorie_max=data.calorie_max,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return pref


@router.patch(
    "/me",
    response_model=UserPreferenceOut,
)
def update_my_preferences(
    data: UserPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partially update the current user's preferences (only provided fields are updated)."""
    pref = get_user_preference(db, current_user.id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not set. Use POST to create.")

    try:
        pref = create_or_update_user_preference(
            db,
            current_user.id,
            # Basic body information
            age=data.age,
            gender=data.gender,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            # Dietary preferences (legacy)
            diet_codes=data.diet_codes,
            allergen_ingredient_ids=data.allergen_ingredient_ids,
            disliked_ingredient_ids=data.disliked_ingredient_ids,
            # Dietary preferences (new)
            diet_type=data.diet_type,
            food_allergies=data.food_allergies,
            # Goal & athlete
            goal=data.goal,
            is_athlete=data.is_athlete,
            training_level=data.training_level,
            # Nutrition targets
            calorie_target=data.calorie_target,
            protein_grams=data.protein_grams,
            carb_grams=data.carb_grams,
            fat_grams=data.fat_grams,
            protein_calories=data.protein_calories,
            carb_calories=data.carb_calories,
            fat_calories=data.fat_calories,
            # Safety range
            calorie_min=data.calorie_min,
            calorie_max=data.calorie_max,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
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
    """Delete the current user's preferences."""
    pref = get_user_preference(db, current_user.id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preferences not set")
    delete_user_preference(db, pref)
    return None
