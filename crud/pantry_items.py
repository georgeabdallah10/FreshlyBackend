# crud/pantry_items.py
from sqlalchemy.orm import Session
from sqlalchemy import asc
from models.pantry_item import PantryItem


def list_pantry_items(db: Session, *, family_id: int) -> list[PantryItem]:
    return (
        db.query(PantryItem)
        .filter(PantryItem.family_id == family_id)
        .order_by(asc(PantryItem.id))
        .all()
    )


def get_pantry_item(db: Session, item_id: int) -> PantryItem | None:
    return db.query(PantryItem).filter(PantryItem.id == item_id).first()


def create_pantry_item(
    db: Session,
    *,
    family_id: int,
    ingredient_id: int,
    quantity: float | None,
    unit_id: int | None,
    expires_at=None,
) -> PantryItem:
    item = PantryItem(
        family_id=family_id,
        ingredient_id=ingredient_id,
        quantity=quantity,
        unit_id=unit_id,
        expires_at=expires_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_pantry_item(
    db: Session,
    item: PantryItem,
    *,
    quantity: float | None = None,
    unit_id: int | None = None,
    expires_at=None,
) -> PantryItem:
    if quantity is not None:
        item.quantity = quantity
    if unit_id is not None:
        item.unit_id = unit_id
    if expires_at is not None:
        item.expires_at = expires_at

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_pantry_item(db: Session, item: PantryItem) -> None:
    db.delete(item)
    db.commit()