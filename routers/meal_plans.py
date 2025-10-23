# routers/meal_plans.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from models.user import User
from models.membership import FamilyMembership
from schemas.meal_plan import MealPlanCreate, MealPlanUpdate, MealPlanOut
from crud.meal_plans import (
    list_meal_plans,
    get_meal_plan,
    create_meal_plan,
    update_meal_plan,
    delete_meal_plan,
)

router = APIRouter(prefix="/meal-plans", tags=["meal_plans"])

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


def _ensure_can_edit(db: Session, user_id: int, family_id: int) -> None:
    m = (
        db.query(FamilyMembership)
        .filter(FamilyMembership.user_id == user_id, FamilyMembership.family_id == family_id)
        .first()
    )
    if not m or m.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


# ---------------- Personal Meal Endpoints ----------------

@router.get("/me", response_model=list[MealPlanOut])
def list_my_meals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_meal_plans(db, created_by_user_id=current_user.id)


@router.post("/me", response_model=MealPlanOut, status_code=status.HTTP_201_CREATED)
def create_my_meal(
    data: MealPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_meal_plan(
        db,
        family_id=None,
        title=data.title,
        start_date=data.start_date,
        end_date=data.end_date,
        created_by_user_id=current_user.id,
    )


@router.patch("/me/{meal_id}", response_model=MealPlanOut)
def update_my_meal(
    meal_id: int,
    data: MealPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meal = get_meal_plan(db, meal_id)
    if not meal or meal.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal not found or unauthorized")
    return update_meal_plan(db, meal, **data.model_dump(exclude_unset=True))


@router.delete("/me/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_meal(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meal = get_meal_plan(db, meal_id)
    if not meal or meal.created_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal not found or unauthorized")
    delete_meal_plan(db, meal)
    return None

@router.get(
    "/family/{family_id}",
    response_model=list[MealPlanOut],
    responses={403: {"model": ErrorOut, "description": "Not a member"}},
)
def list_for_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_member(db, current_user.id, family_id)
    return list_meal_plans(db, family_id=family_id)


@router.get(
    "/{plan_id}",
    response_model=MealPlanOut,
    responses={404: {"model": ErrorOut, "description": "Meal plan not found"}},
)
def get_one_plan(plan_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return plan


@router.post(
    "",
    response_model=MealPlanOut,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorOut, "description": "Not a member"}},
)
def create_one_plan(
    data: MealPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_member(db, current_user.id, data.family_id)
    return create_meal_plan(
        db,
        family_id=data.family_id,
        title=data.title,
        start_date=data.start_date,
        end_date=data.end_date,
        created_by_user_id=current_user.id,
    )



@router.patch(
    "/{plan_id}",
    response_model=MealPlanOut,
    responses={
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
        404: {"model": ErrorOut, "description": "Meal plan not found"},
    },
)
def update_one_plan(
    plan_id: int,
    data: MealPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    _ensure_can_edit(db, current_user.id, plan.family_id)
    return update_meal_plan(db, plan, **data.model_dump(exclude_unset=True))


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
        404: {"model": ErrorOut, "description": "Meal plan not found"},
    },
)
def delete_one_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    _ensure_can_edit(db, current_user.id, plan.family_id)
    delete_meal_plan(db, plan)
    return None

