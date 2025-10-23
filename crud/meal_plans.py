# crud/meal_plans.py
from sqlalchemy.orm import Session
from sqlalchemy import asc
from models.meal_plan import MealPlan
from datetime import date
from models.user import User  # if you want a typed param



def list_meal_plans(
    db: Session,
    user: User | None = None,
    created_by_user_id: int | None = None,
):
    query = db.query(MealPlan)

    # Guard: avoid returning ALL meal plans accidentally
    if created_by_user_id is None and user is None:
        return []

    if created_by_user_id is not None:
        query = query.filter(MealPlan.created_by_user_id == created_by_user_id)
    elif user is not None:
        # family-scoped
        family_ids = [m.family_id for m in user.memberships]
        query = query.filter(MealPlan.family_id.in_(family_ids))

    plans = query.all()
    return plans or [] 


def get_meal_plan(db: Session, plan_id: int) -> MealPlan | None:
    return db.query(MealPlan).filter(MealPlan.id == plan_id).first()


def create_meal_plan(
    db: Session,
    *,
    family_id: int,
    title: str,
    start_date: date,
    end_date: date | None,
    created_by_user_id: int,
) -> MealPlan:
    # Guard: if an end_date is provided, it must be on/after start_date
    if end_date is not None and end_date < start_date:
        raise ValueError("end_date cannot be before start_date")
    plan = MealPlan(
        family_id=family_id,
        title=title,
        start_date=start_date,
        end_date=end_date,
        created_by_user_id=created_by_user_id,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_meal_plan(
    db: Session,
    plan: MealPlan,
    *,
    title: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> MealPlan:
    if title is not None:
        plan.title = title
    if start_date is not None:
        plan.start_date = start_date
    if end_date is not None:
        plan.end_date = end_date

    # Guard: validate final range if both dates are set
    if plan.end_date is not None and plan.start_date is not None and plan.end_date < plan.start_date:
        raise ValueError("end_date cannot be before start_date")

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def delete_meal_plan(db: Session, plan: MealPlan) -> None:
    db.delete(plan)
    db.commit()