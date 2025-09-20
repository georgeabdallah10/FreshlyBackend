# crud/grocery_lists.py
from sqlalchemy.orm import Session
from sqlalchemy import asc
from models.grocery_list import GroceryList


def list_grocery_lists(db: Session, *, family_id: int) -> list[GroceryList]:
    return (
        db.query(GroceryList)
        .filter(GroceryList.family_id == family_id)
        .order_by(asc(GroceryList.id))
        .all()
    )


def get_grocery_list(db: Session, list_id: int) -> GroceryList | None:
    return db.query(GroceryList).filter(GroceryList.id == list_id).first()


def create_grocery_list(
    db: Session,
    *,
    family_id: int,
    title: str | None = None,
    status: str | None = None,
    meal_plan_id: int | None = None,
) -> GroceryList:
    g = GroceryList(
        family_id=family_id,
        title=title,
        status=status or "draft",
        meal_plan_id=meal_plan_id,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def update_grocery_list(
    db: Session,
    g: GroceryList,
    *,
    title: str | None = None,
    status: str | None = None,
    meal_plan_id: int | None = None,
) -> GroceryList:
    if title is not None:
        g.title = title
    if status is not None:
        g.status = status
    if meal_plan_id is not None:
        g.meal_plan_id = meal_plan_id
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def delete_grocery_list(db: Session, g: GroceryList) -> None:
    db.delete(g)
    db.commit()