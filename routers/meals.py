# routers/meals.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user
from models.user import User
from crud.meals import (
    create_meal, list_meals, get_meal, update_meal, delete_meal,
    share_meal_with_family, unshare_meal_with_family, list_family_shared_meals
)
from schemas.meal import MealCreate, MealOut

router = APIRouter(prefix="/meals", tags=["meals"])

@router.get("/me", response_model=list[MealOut])
def list_my_meals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_meals(db, created_by_user_id=current_user.id)

@router.post("/me", response_model=MealOut, status_code=status.HTTP_201_CREATED)
def create_my_meal(data: MealCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_meal(db, data, created_by_user_id=current_user.id)

@router.patch("/me/{meal_id}", response_model=MealOut)
def update_my_meal(meal_id: int, data: MealCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meal = get_meal(db, meal_id)
    if not meal or meal.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal not found or unauthorized")
    return update_meal(db, meal, data)

@router.delete("/me/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_meal(meal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meal = get_meal(db, meal_id)
    if not meal or meal.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal not found or unauthorized")
    delete_meal(db, meal)
    return None

# Family meal sharing endpoints
@router.post("/me/{meal_id}/share", response_model=MealOut)
def share_meal(meal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Share a meal with your family. Only the meal creator can share their meals."""
    meal = get_meal(db, meal_id)
    if not meal or meal.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal not found or unauthorized")
    if not meal.family_id:
        raise HTTPException(status_code=400, detail="Meal must belong to a family to be shared")
    if meal.shared_with_family:
        raise HTTPException(status_code=400, detail="Meal is already shared with family")
    return share_meal_with_family(db, meal)

@router.delete("/me/{meal_id}/share", response_model=MealOut)
def unshare_meal(meal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Unshare a meal from your family. Only the meal creator can unshare their meals."""
    meal = get_meal(db, meal_id)
    if not meal or meal.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal not found or unauthorized")
    if not meal.shared_with_family:
        raise HTTPException(status_code=400, detail="Meal is not currently shared with family")
    return unshare_meal_with_family(db, meal)

@router.get("/family/{family_id}/shared", response_model=list[MealOut])
def get_family_shared_meals(family_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all meals shared with a specific family. Any family member can view shared meals."""
    # Check if user is a member of this family
    from models.membership import FamilyMembership
    membership = db.query(FamilyMembership).filter(
        FamilyMembership.family_id == family_id,
        FamilyMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this family")
    return list_family_shared_meals(db, family_id)