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

    def sync_list_with_pantry(
        self,
        db: Session,
        list_id: int,
    ) -> tuple[int, int]:
        """
        Recalculate grocery list based on current pantry inventory.
        Removes items now in pantry, adds items now missing.

        Args:
            db: Database session
            list_id: Grocery list to sync

        Returns:
            (items_removed, items_updated)
        """
        logger.info(f"Syncing list {list_id} with pantry")

        # Get list with items
        grocery_list = get_grocery_list(db, list_id, load_items=True)
        if not grocery_list:
            raise ValueError(f"Grocery list {list_id} not found")

        # Get pantry inventory
        include_family = (grocery_list.owner_user_id is not None)
        pantry_inventory = get_pantry_inventory(
            db,
            family_id=grocery_list.family_id,
            owner_user_id=grocery_list.owner_user_id,
            include_family_for_user=include_family,
        )

        items_removed = 0
        items_updated = 0

        # Check each item against pantry
        for item in grocery_list.items:
            if item.checked:
                # Skip checked items
                continue

            key = (item.ingredient_id, item.unit_id)
            available_qty = pantry_inventory.get(key, Decimal(0))
            required_qty = item.quantity or Decimal(0)

            if available_qty >= required_qty:
                # Item now fully in pantry - remove from list
                db.delete(item)
                items_removed += 1
            elif available_qty > 0:
                # Partially in pantry - update quantity
                item.quantity = required_qty - available_qty
                item.note = "Quantity adjusted based on pantry inventory"
                db.add(item)
                items_updated += 1

        db.commit()

        logger.info(
            f"Sync complete: {items_removed} removed, {items_updated} updated"
        )

        return items_removed, items_updated

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
