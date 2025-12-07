"""
Grocery List Service

Handles business logic for grocery list operations including:
- Recipe-to-list conversion
- Pantry comparison
- Missing ingredient calculation
"""
import logging
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional

from crud.grocery_lists import (
    get_recipe_ingredients,
    get_pantry_inventory,
    calculate_missing_ingredients,
    add_items_to_list,
    create_grocery_list,
    get_grocery_list,
)
from crud.recipes import get_recipe
from crud.meals import get_meal
from crud.ingredients import get_ingredient_by_name, create_ingredient
from models.grocery_list import GroceryList
from models.membership import FamilyMembership

logger = logging.getLogger(__name__)


class GroceryListService:
    """Service for grocery list business logic"""

    def generate_missing_ingredients(
        self,
        db: Session,
        recipe_id: int,
        family_id: int | None = None,
        owner_user_id: int | None = None,
        servings_multiplier: float = 1.0,
    ) -> list[dict]:
        """
        Generate list of missing ingredients for a recipe.

        Args:
            db: Database session
            recipe_id: Recipe to analyze
            family_id: Family scope (for family recipe/list)
            owner_user_id: User scope (for personal recipe/list)
            servings_multiplier: Scale recipe quantities

        Returns:
            List of missing ingredient dicts
        """
        logger.info(
            f"Generating missing ingredients for recipe {recipe_id}, "
            f"family={family_id}, user={owner_user_id}"
        )

        # Get recipe ingredients
        recipe_ingredients = get_recipe_ingredients(db, recipe_id)

        if not recipe_ingredients:
            logger.warning(f"Recipe {recipe_id} has no ingredients")
            return []

        # Get pantry inventory
        # If personal list, check both personal and family pantry
        include_family = (owner_user_id is not None)

        pantry_inventory = get_pantry_inventory(
            db,
            family_id=family_id,
            owner_user_id=owner_user_id,
            include_family_for_user=include_family,
        )

        # Calculate missing
        missing = calculate_missing_ingredients(
            recipe_ingredients,
            pantry_inventory,
            servings_multiplier,
        )

        logger.info(f"Found {len(missing)} missing ingredients")
        return missing

    def add_recipe_to_list(
        self,
        db: Session,
        recipe_id: int,
        list_id: int | None = None,
        family_id: int | None = None,
        owner_user_id: int | None = None,
        title: str | None = None,
        servings_multiplier: float = 1.0,
    ) -> tuple[GroceryList, int]:
        """
        Add recipe ingredients to grocery list (create new or use existing).

        Args:
            db: Database session
            recipe_id: Recipe to add
            list_id: Existing list ID (optional)
            family_id: Family scope for new list
            owner_user_id: User scope for new list
            title: Title for new list
            servings_multiplier: Scale recipe quantities

        Returns:
            (GroceryList, items_added_count)
        """
        logger.info(f"Adding recipe {recipe_id} to list {list_id}")

        # Validate recipe exists
        recipe = get_recipe(db, recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")

        # Get or create list
        if list_id:
            grocery_list = get_grocery_list(db, list_id)
            if not grocery_list:
                raise ValueError(f"Grocery list {list_id} not found")
        else:
            # Create new list
            if title is None:
                title = f"Shopping list for {recipe.title}"

            grocery_list = create_grocery_list(
                db,
                family_id=family_id,
                owner_user_id=owner_user_id,
                title=title,
                status="draft",
            )

        # Generate missing ingredients
        missing = self.generate_missing_ingredients(
            db,
            recipe_id,
            family_id=grocery_list.family_id,
            owner_user_id=grocery_list.owner_user_id,
            servings_multiplier=servings_multiplier,
        )

        if not missing:
            logger.info("No missing ingredients - all items in pantry")
            return grocery_list, 0

        # Add items to list
        items_added = add_items_to_list(
            db,
            grocery_list.id,
            missing,
        )

        logger.info(
            f"Added {len(items_added)} items to list {grocery_list.id}"
        )

        return grocery_list, len(items_added)

    def add_meal_to_list(
        self,
        db: Session,
        meal_id: int,
        list_id: int | None = None,
        family_id: int | None = None,
        owner_user_id: int | None = None,
        title: str | None = None,
        servings_multiplier: float = 1.0,
    ) -> tuple[GroceryList, int]:
        """
        Add meal ingredients to grocery list (create new or use existing).

        Args:
            db: Database session
            meal_id: Meal to add
            list_id: Existing list ID (optional)
            family_id: Family scope for new list
            owner_user_id: User scope for new list
            title: Title for new list
            servings_multiplier: Scale meal quantities

        Returns:
            (GroceryList, items_added_count)
        """
        logger.info(f"Adding meal {meal_id} to list {list_id}")

        # Validate meal exists
        meal = get_meal(db, meal_id)
        if not meal:
            raise ValueError(f"Meal {meal_id} not found")

        # Get or create list
        if list_id:
            grocery_list = get_grocery_list(db, list_id)
            if not grocery_list:
                raise ValueError(f"Grocery list {list_id} not found")
        else:
            # Create new list
            if title is None:
                title = f"Shopping list for {meal.name}"

            grocery_list = create_grocery_list(
                db,
                family_id=family_id,
                owner_user_id=owner_user_id,
                title=title,
                status="draft",
            )

        # Get ingredients from meal (JSONB field)
        # Meal ingredients format: [{"name": "flour", "amount": "2 cups", "inPantry": false}, ...]
        meal_ingredients = meal.ingredients or []

        if not meal_ingredients:
            logger.info("Meal has no ingredients")
            return grocery_list, 0

        # Filter out items already in pantry and convert to grocery list items
        items_to_add = []
        for ingredient in meal_ingredients:
            # Skip items marked as in pantry
            in_pantry = ingredient.get("in_pantry") or ingredient.get("inPantry", False)
            if in_pantry:
                continue

            name = ingredient.get("name", "")
            amount = ingredient.get("amount", "")

            if not name:
                continue

            # Add as grocery list item with the name and amount as note
            # Since meal ingredients are not normalized, we store the raw info
            items_to_add.append({
                "ingredient_name": name,
                "quantity_text": amount,
                "note": f"{amount}" if amount else None,
            })

        if not items_to_add:
            logger.info("No missing ingredients - all items in pantry")
            return grocery_list, 0

        # Add items to list using the raw ingredient approach
        items_added = self._add_meal_ingredients_to_list(
            db,
            grocery_list.id,
            items_to_add,
        )

        logger.info(
            f"Added {items_added} items to list {grocery_list.id}"
        )

        return grocery_list, items_added

    def _add_meal_ingredients_to_list(
        self,
        db: Session,
        grocery_list_id: int,
        items_data: list[dict],
    ) -> int:
        """
        Add meal ingredients to grocery list.
        Looks up or creates ingredients by name, then adds to list.
        """
        from models.grocery_list import GroceryListItem

        created_count = 0
        for data in items_data:
            ingredient_name = data.get("ingredient_name", "").strip().lower()
            quantity_text = data.get("quantity_text", "")

            if not ingredient_name:
                continue

            # Look up or create ingredient by name
            ingredient = get_ingredient_by_name(db, ingredient_name)
            if not ingredient:
                # Create new ingredient
                try:
                    ingredient = create_ingredient(db, name=ingredient_name, category=None)
                except Exception as e:
                    logger.warning(f"Failed to create ingredient '{ingredient_name}': {e}")
                    # Try to fetch again in case of race condition
                    ingredient = get_ingredient_by_name(db, ingredient_name)
                    if not ingredient:
                        continue

            # Check if item with same ingredient already exists in this list
            existing = db.query(GroceryListItem).filter(
                GroceryListItem.grocery_list_id == grocery_list_id,
                GroceryListItem.ingredient_id == ingredient.id
            ).first()

            if existing:
                # Update note if needed
                if quantity_text and quantity_text not in (existing.note or ""):
                    existing.note = f"{existing.note}, {quantity_text}" if existing.note else quantity_text
                    db.add(existing)
                continue

            # Create new item with proper ingredient_id
            new_item = GroceryListItem(
                grocery_list_id=grocery_list_id,
                ingredient_id=ingredient.id,
                quantity=None,  # Raw text amount stored in note
                unit_id=None,
                note=quantity_text if quantity_text else None,
                checked=False,
            )
            db.add(new_item)
            created_count += 1

        db.commit()
        return created_count

    def sync_list_with_pantry(
        self,
        db: Session,
        grocery_list: GroceryList,
    ) -> tuple[int, int, GroceryList]:
        """
        ACID-safe pantry sync with updated_at tracking.

        Compares grocery list items against pantry inventory and:
        - Removes items fully covered by pantry
        - Reduces quantities for partially covered items

        Args:
            db: Database session
            grocery_list: Pre-loaded GroceryList with items

        Returns:
            (items_removed, items_updated, updated_grocery_list)
        """
        from datetime import datetime, timezone

        logger.info(f"Syncing list {grocery_list.id} with pantry")

        # Get pantry inventory
        # For personal lists, also check family pantry
        include_family = (grocery_list.owner_user_id is not None)
        pantry_inventory = get_pantry_inventory(
            db,
            family_id=grocery_list.family_id,
            owner_user_id=grocery_list.owner_user_id,
            include_family_for_user=include_family,
        )

        items_removed = 0
        items_updated = 0

        # Process each unchecked item (copy list to allow deletion during iteration)
        for item in list(grocery_list.items):
            if item.checked:
                # Skip checked items - user already marked as purchased
                continue

            key = (item.ingredient_id, item.unit_id)
            pantry_qty = pantry_inventory.get(key, Decimal(0))
            required_qty = item.quantity or Decimal(0)

            if pantry_qty >= required_qty:
                # Fully covered by pantry - remove from grocery list
                db.delete(item)
                items_removed += 1
            elif pantry_qty > 0 and required_qty > 0:
                # Partially covered - reduce grocery list quantity
                item.quantity = required_qty - pantry_qty
                items_updated += 1

        # Update timestamp explicitly (triggers onupdate behavior)
        grocery_list.updated_at = datetime.now(timezone.utc)

        # Single commit - ACID transaction
        db.commit()
        db.refresh(grocery_list)

        logger.info(
            f"Sync complete for list {grocery_list.id}: "
            f"{items_removed} removed, {items_updated} updated"
        )

        return items_removed, items_updated, grocery_list

    def validate_list_access(
        self,
        db: Session,
        grocery_list: GroceryList,
        user_id: int,
    ) -> bool:
        """
        Check if user has access to grocery list.

        Args:
            db: Database session
            grocery_list: GroceryList to check
            user_id: User requesting access

        Returns:
            True if user has access, False otherwise
        """
        # Personal list - must be owner
        if grocery_list.owner_user_id:
            return grocery_list.owner_user_id == user_id

        # Family list - must be member
        if grocery_list.family_id:
            membership = db.query(FamilyMembership).filter(
                FamilyMembership.family_id == grocery_list.family_id,
                FamilyMembership.user_id == user_id,
            ).first()
            return membership is not None

        return False


# Singleton instance
grocery_list_service = GroceryListService()
