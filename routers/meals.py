# routers/meals.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user
from models.user import User
from crud.meals import create_meal, list_meals, get_meal, update_meal, delete_meal
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