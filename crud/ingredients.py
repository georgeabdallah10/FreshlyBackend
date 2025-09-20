# crud/ingredients.py
from sqlalchemy.orm import Session
from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError
from models.ingredient import Ingredient


def list_ingredients(db: Session) -> list[Ingredient]:
    """Return all ingredients ordered by name."""
    return db.query(Ingredient).order_by(asc(Ingredient.name)).all()


def get_ingredient(db: Session, ingredient_id: int) -> Ingredient | None:
    """Return a single ingredient by id."""
    return db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()


def get_ingredient_by_name(db: Session, name: str) -> Ingredient | None:
    """Return an ingredient by exact name (used for uniqueness checks)."""
    return db.query(Ingredient).filter(Ingredient.name == name).first()


def create_ingredient(db: Session, *, name: str, category: str | None) -> Ingredient:
    """Create a new ingredient."""
    ing = Ingredient(name=name, category=category)
    db.add(ing)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(ing)
    return ing


def update_ingredient(
    db: Session,
    ing: Ingredient,
    *,
    name: str | None = None,
    category: str | None = None,
) -> Ingredient:
    """Update an existing ingredient."""
    if name is not None:
        ing.name = name
    if category is not None:
        ing.category = category

    db.add(ing)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(ing)
    return ing


def delete_ingredient(db: Session, ing: Ingredient) -> None:
    """Delete an ingredient. Will fail if referenced by FKs with RESTRICT."""
    db.delete(ing)
    db.commit()