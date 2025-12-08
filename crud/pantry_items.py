# crud/pantry_items.py
from sqlalchemy.orm import Session
from sqlalchemy import asc, func
from models.pantry_item import PantryItem
from models.ingredient import Ingredient
from datetime import datetime
from decimal import Decimal
from services.unit_normalizer import try_normalize_quantity
import logging

logger = logging.getLogger(__name__)


def get_pantry_item(db: Session, item_id: int) -> PantryItem | None:
    return db.query(PantryItem).filter(PantryItem.id == item_id).first()


def create_pantry_item(
    db: Session,
    *,
    ingredient_id: int,
    quantity: int | float | Decimal | None,
    unit: str | None,
    family_id: int | None,
    owner_user_id: int | None,
    category: str | None,
    expires_at: datetime | None = None
) -> PantryItem:
    """
    Create a new pantry item with automatic unit normalization.

    If the ingredient has canonical unit metadata, the quantity will be
    normalized and stored in canonical_quantity/canonical_unit fields.
    """
    # Fetch ingredient for normalization
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

    # Calculate canonical values if possible
    canonical_quantity = None
    canonical_unit = None

    if ingredient and quantity is not None and unit:
        qty_float = float(quantity) if quantity is not None else None
        canonical_quantity, canonical_unit = try_normalize_quantity(
            ingredient, qty_float, unit
        )
        if canonical_quantity is not None:
            canonical_quantity = Decimal(str(canonical_quantity))

    item = PantryItem(
        ingredient_id=ingredient_id,
        quantity=quantity,
        unit=unit,
        family_id=family_id,
        owner_user_id=owner_user_id,
        category=(category.strip() if category else None),
        expires_at=expires_at,
        canonical_quantity=canonical_quantity,
        canonical_unit=canonical_unit,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
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


def update_pantry_item(
    db: Session,
    item: PantryItem,
    *,
    ingredient_id: int | None = None,
    quantity: int | float | Decimal | None = None,
    unit: str | None = None,
    expires_at: datetime | None = None,
    category: str | None = None
) -> PantryItem:
    """
    Update a pantry item with automatic unit normalization.

    If quantity or unit changes, canonical values will be recalculated.
    """
    if ingredient_id is not None:
        item.ingredient_id = ingredient_id
    if quantity is not None:
        item.quantity = quantity
    if unit is not None:
        item.unit = unit
    if expires_at is not None:
        item.expires_at = expires_at
    if category is not None:
        item.category = category.strip() or None

    # Recalculate canonical values if quantity or unit changed
    if quantity is not None or unit is not None:
        # Fetch the ingredient for normalization
        ingredient = db.query(Ingredient).filter(
            Ingredient.id == item.ingredient_id
        ).first()

        if ingredient and item.quantity is not None and item.unit:
            qty_float = float(item.quantity)
            canonical_quantity, canonical_unit = try_normalize_quantity(
                ingredient, qty_float, item.unit
            )
            if canonical_quantity is not None:
                item.canonical_quantity = Decimal(str(canonical_quantity))
                item.canonical_unit = canonical_unit
            else:
                # Normalization failed - clear canonical fields
                item.canonical_quantity = None
                item.canonical_unit = None
        else:
            item.canonical_quantity = None
            item.canonical_unit = None

    db.add(item)
    db.commit()
    db.refresh(item)
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


def recalculate_canonical_quantity(db: Session, item: PantryItem) -> PantryItem:
    """
    Recalculate canonical quantity for an existing pantry item.

    Useful when ingredient metadata is updated.
    """
    if item.quantity is None or item.unit is None:
        item.canonical_quantity = None
        item.canonical_unit = None
    else:
        ingredient = db.query(Ingredient).filter(
            Ingredient.id == item.ingredient_id
        ).first()

        if ingredient:
            qty_float = float(item.quantity)
            canonical_quantity, canonical_unit = try_normalize_quantity(
                ingredient, qty_float, item.unit
            )
            if canonical_quantity is not None:
                item.canonical_quantity = Decimal(str(canonical_quantity))
                item.canonical_unit = canonical_unit
            else:
                item.canonical_quantity = None
                item.canonical_unit = None
        else:
            item.canonical_quantity = None
            item.canonical_unit = None

    db.add(item)
    db.commit()
    db.refresh(item)
    return item
