# crud/pantry_items.py
from sqlalchemy.orm import Session
from sqlalchemy import asc, func
from models.pantry_item import PantryItem
from models.ingredient import Ingredient
from datetime import datetime

def get_pantry_item(db: Session, item_id: int) -> PantryItem | None:
    return db.query(PantryItem).filter(PantryItem.id == item_id).first()


def create_pantry_item(db: Session, *, ingredient_id: int, quantity: int | None,
                       unit: str | None, family_id: int | None, owner_user_id: int | None,
                       category: str | None, expires_at: datetime | None = None):
    item = PantryItem(
        ingredient_id=ingredient_id,
        quantity=quantity,
        unit=unit,
        family_id=family_id,
        owner_user_id=owner_user_id,
        category=(category.strip() if category else None),
        expires_at=expires_at
    )
    db.add(item); db.commit(); db.refresh(item)
    return item

def list_pantry_items(
    db: Session,
    *,
    family_id: int | None = None,
    owner_user_id: int | None = None,
) -> list[PantryItem]:
    q = db.query(PantryItem)
    if family_id is not None:
        q = q.filter(PantryItem.family_id == family_id)
    if owner_user_id is not None:
        q = q.filter(PantryItem.owner_user_id == owner_user_id)
    return q.all() or []

def update_pantry_item(db: Session, item: PantryItem, *,
                       ingredient_id: int | None = None,
                       quantity: int | None = None,
                       unit: str | None = None,
                       expires_at: datetime | None = None,
                       category: str | None = None):
    if ingredient_id is not None: item.ingredient_id = ingredient_id
    if quantity is not None: item.quantity = quantity
    if unit is not None: item.unit = unit
    if expires_at is not None: item.expires_at = expires_at
    if category is not None: item.category = category.strip() or None
    db.add(item); db.commit(); db.refresh(item)
    return item

def delete_pantry_item(db: Session, item: PantryItem) -> None:
    db.delete(item)
    db.commit()


# --- utility ---
def create_or_get_ingredient(db: Session, name: str) -> Ingredient:
    """Return existing Ingredient by case-insensitive name, or create it.

    Normalizes whitespace; ensures single row per logical name.
    """
    normalized = (name or "").strip()
    if not normalized:
        raise ValueError("Ingredient name cannot be empty")

    existing = (
        db.query(Ingredient)
        .filter(func.lower(Ingredient.name) == normalized.lower())
        .first()
    )
    if existing:
        return existing

    ing = Ingredient(name=normalized)
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing
