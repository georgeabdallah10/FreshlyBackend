# crud/meal_plans.py
from sqlalchemy.orm import Session
from sqlalchemy import asc
from models.meal_plan import MealPlan
from datetime import date


def list_meal_plans(db: Session, *, family_id: int) -> list[MealPlan]:
    return (
        db.query(MealPlan)
        .filter(MealPlan.family_id == family_id)
        .order_by(asc(MealPlan.start_date))
        .all()
    )


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