# crud/grocery_lists.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import asc, or_
from models.grocery_list import GroceryList, GroceryListItem
from models.recipe_ingredient import RecipeIngredient
from models.pantry_item import PantryItem
from models.ingredient import Ingredient
from models.unit import Unit
from decimal import Decimal
from typing import Optional


# ===== GroceryList CRUD =====

def list_grocery_lists(
    db: Session,
    *,
    family_id: int | None = None,
    owner_user_id: int | None = None,
    status: str | None = None
) -> list[GroceryList]:
    """List grocery lists with dual-scope support"""
    query = db.query(GroceryList).options(
        joinedload(GroceryList.items)
            .joinedload(GroceryListItem.ingredient),
        joinedload(GroceryList.items)
            .joinedload(GroceryListItem.unit)
    )

    if family_id is not None:
        query = query.filter(GroceryList.family_id == family_id)
    if owner_user_id is not None:
        query = query.filter(GroceryList.owner_user_id == owner_user_id)
    if status is not None:
        query = query.filter(GroceryList.status == status)

    return query.order_by(asc(GroceryList.created_at)).all()


def get_grocery_list(
    db: Session,
    list_id: int,
    load_items: bool = True
) -> GroceryList | None:
    """Get grocery list with optional eager loading of items"""
    query = db.query(GroceryList)

    if load_items:
        query = query.options(
            joinedload(GroceryList.items)
                .joinedload(GroceryListItem.ingredient),
            joinedload(GroceryList.items)
                .joinedload(GroceryListItem.unit)
        )

    return query.filter(GroceryList.id == list_id).first()


def create_grocery_list(
    db: Session,
    *,
    family_id: int | None = None,
    owner_user_id: int | None = None,
    title: str | None = None,
    status: str = "draft",
    meal_plan_id: int | None = None,
) -> GroceryList:
    """Create grocery list with dual-scope support"""
    # Validate XOR constraint
    if (family_id is None) == (owner_user_id is None):
        raise ValueError(
            "Exactly one of family_id or owner_user_id must be provided"
        )

    g = GroceryList(
        family_id=family_id,
        owner_user_id=owner_user_id,
        title=title,
        status=status,
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
    """Update grocery list fields"""
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
    """Delete grocery list (cascade deletes items)"""
    db.delete(g)
    db.commit()


# ===== GroceryListItem CRUD =====

def get_grocery_list_item(db: Session, item_id: int) -> GroceryListItem | None:
    """Get a single grocery list item"""
    return db.query(GroceryListItem).filter(
        GroceryListItem.id == item_id
    ).first()


def create_grocery_list_item(
    db: Session,
    *,
    grocery_list_id: int,
    ingredient_id: int,
    quantity: Decimal | None = None,
    unit_id: int | None = None,
    checked: bool = False,
    note: str | None = None,
) -> GroceryListItem:
    """Create a single grocery list item"""
    item = GroceryListItem(
        grocery_list_id=grocery_list_id,
        ingredient_id=ingredient_id,
        quantity=quantity,
        unit_id=unit_id,
        checked=checked,
        note=note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def bulk_create_grocery_list_items(
    db: Session,
    items_data: list[dict]
) -> list[GroceryListItem]:
    """Bulk create grocery list items for efficiency"""
    items = [GroceryListItem(**data) for data in items_data]
    db.add_all(items)
    db.commit()

    # Refresh all items
    for item in items:
        db.refresh(item)

    return items


def update_grocery_list_item(
    db: Session,
    item: GroceryListItem,
    *,
    quantity: Decimal | None = None,
    unit_id: int | None = None,
    checked: bool | None = None,
    note: str | None = None,
) -> GroceryListItem:
    """Update grocery list item"""
    if quantity is not None:
        item.quantity = quantity
    if unit_id is not None:
        item.unit_id = unit_id
    if checked is not None:
        item.checked = checked
    if note is not None:
        item.note = note

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_grocery_list_item(db: Session, item: GroceryListItem) -> None:
    """Delete a grocery list item"""
    db.delete(item)
    db.commit()


def clear_checked_items(db: Session, grocery_list_id: int) -> int:
    """Clear all checked items from a list. Returns count deleted."""
    deleted = db.query(GroceryListItem).filter(
        GroceryListItem.grocery_list_id == grocery_list_id,
        GroceryListItem.checked == True
    ).delete()
    db.commit()
    return deleted


# ===== Helper Functions for Recipe Integration =====

def get_recipe_ingredients(
    db: Session,
    recipe_id: int
) -> list[RecipeIngredient]:
    """Fetch all ingredients for a recipe with relationships loaded"""
    return db.query(RecipeIngredient).options(
        joinedload(RecipeIngredient.ingredient),
        joinedload(RecipeIngredient.unit)
    ).filter(
        RecipeIngredient.recipe_id == recipe_id
    ).all()


def get_pantry_inventory(
    db: Session,
    family_id: int | None = None,
    owner_user_id: int | None = None,
    include_family_for_user: bool = False,
) -> dict[tuple[int, int | None], Decimal]:
    """
    Get pantry inventory as a dict keyed by (ingredient_id, unit_id).

    Args:
        family_id: Get family pantry
        owner_user_id: Get personal pantry
        include_family_for_user: If True and owner_user_id provided,
                                 also include family pantry from user's families

    Returns:
        Dict mapping (ingredient_id, unit_id) -> total_quantity
    """
    query = db.query(PantryItem).options(
        joinedload(PantryItem.ingredient)
    )

    if family_id is not None:
        query = query.filter(PantryItem.family_id == family_id)
    elif owner_user_id is not None:
        if include_family_for_user:
            # Get user's family memberships
            from models.membership import FamilyMembership
            family_ids = db.query(FamilyMembership.family_id).filter(
                FamilyMembership.user_id == owner_user_id
            ).all()
            family_ids = [fid[0] for fid in family_ids]

            # Include both personal and family pantry items
            query = query.filter(
                or_(
                    PantryItem.owner_user_id == owner_user_id,
                    PantryItem.family_id.in_(family_ids)
                )
            )
        else:
            query = query.filter(PantryItem.owner_user_id == owner_user_id)

    items = query.all()

    # Build inventory dict
    # Note: PantryItem.unit is a string, not unit_id
    # We need to resolve string unit to unit_id for comparison
    inventory = {}

    for item in items:
        if item.ingredient_id is None or item.quantity is None:
            continue

        # Try to resolve unit string to unit_id
        unit_id = None
        if item.unit:
            unit_obj = db.query(Unit).filter(
                Unit.code == item.unit
            ).first()
            if unit_obj:
                unit_id = unit_obj.id

        key = (item.ingredient_id, unit_id)
        inventory[key] = inventory.get(key, Decimal(0)) + item.quantity

    return inventory


def calculate_missing_ingredients(
    recipe_ingredients: list[RecipeIngredient],
    pantry_inventory: dict[tuple[int, int | None], Decimal],
    servings_multiplier: float = 1.0,
) -> list[dict]:
    """
    Calculate missing ingredients by comparing recipe to pantry.

    Args:
        recipe_ingredients: List of RecipeIngredient objects
        pantry_inventory: Dict from get_pantry_inventory()
        servings_multiplier: Scale recipe quantities (e.g., 2.0 for double)

    Returns:
        List of dicts with ingredient_id, quantity, unit_id, note
    """
    missing = []

    for recipe_ing in recipe_ingredients:
        ingredient_id = recipe_ing.ingredient_id
        required_qty = (recipe_ing.quantity or Decimal(0)) * Decimal(servings_multiplier)
        unit_id = recipe_ing.unit_id

        # Check if we have this ingredient with exact unit match
        key = (ingredient_id, unit_id)
        available_qty = pantry_inventory.get(key, Decimal(0))

        if available_qty < required_qty:
            # Need to add to list
            needed_qty = required_qty - available_qty

            missing.append({
                "ingredient_id": ingredient_id,
                "quantity": needed_qty,
                "unit_id": unit_id,
                "note": None,
            })

        # Check for unit mismatch (same ingredient, different unit)
        for (inv_ing_id, inv_unit_id), inv_qty in pantry_inventory.items():
            if inv_ing_id == ingredient_id and inv_unit_id != unit_id and inv_qty > 0:
                # Unit mismatch detected
                if not any(m["ingredient_id"] == ingredient_id for m in missing):
                    # Add with note about mismatch
                    missing.append({
                        "ingredient_id": ingredient_id,
                        "quantity": required_qty,
                        "unit_id": unit_id,
                        "note": "Unit mismatch detected in pantry - please verify quantity",
                    })
                else:
                    # Already added, update note
                    for m in missing:
                        if m["ingredient_id"] == ingredient_id:
                            m["note"] = "Unit mismatch detected in pantry - please verify quantity"

    return missing


def add_items_to_list(
    db: Session,
    grocery_list_id: int,
    items_data: list[dict],
) -> list[GroceryListItem]:
    """
    Bulk add items to a grocery list.
    Handles duplicates by updating quantity instead of creating new item.

    Args:
        items_data: List of dicts with keys: ingredient_id, quantity, unit_id, note
    """
    existing_items = db.query(GroceryListItem).filter(
        GroceryListItem.grocery_list_id == grocery_list_id
    ).all()

    # Build map of existing items by (ingredient_id, unit_id)
    existing_map = {}
    for item in existing_items:
        key = (item.ingredient_id, item.unit_id)
        existing_map[key] = item

    created_items = []
    updated_items = []

    for data in items_data:
        key = (data["ingredient_id"], data.get("unit_id"))

        if key in existing_map:
            # Update existing item
            item = existing_map[key]
            item.quantity = (item.quantity or Decimal(0)) + (data.get("quantity") or Decimal(0))
            if data.get("note"):
                item.note = data["note"]
            item.checked = False  # Uncheck if new quantity added
            updated_items.append(item)
        else:
            # Create new item
            new_item = GroceryListItem(
                grocery_list_id=grocery_list_id,
                ingredient_id=data["ingredient_id"],
                quantity=data.get("quantity"),
                unit_id=data.get("unit_id"),
                note=data.get("note"),
                checked=False,
            )
            created_items.append(new_item)

    # Save all changes
    if created_items:
        db.add_all(created_items)
    if updated_items:
        for item in updated_items:
            db.add(item)

    db.commit()

    # Refresh all items
    all_items = created_items + updated_items
    for item in all_items:
        db.refresh(item)

    return all_items
