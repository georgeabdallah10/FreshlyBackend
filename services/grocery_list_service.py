"""
Grocery List Service

Handles business logic for grocery list operations including:
- Recipe-to-list conversion
- Pantry comparison
- Missing ingredient calculation
- Phase 3: Smart syncing between pantry and grocery lists
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

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
from models.grocery_list import GroceryList, GroceryListItem
from models.membership import FamilyMembership
from models.pantry_item import PantryItem
from models.ingredient import Ingredient

if TYPE_CHECKING:
    from models.grocery_list import GroceryListItem
    from models.pantry_item import PantryItem

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

    def _find_best_matching_ingredient(
        self,
        db: Session,
        ingredient_name: str,
    ) -> Ingredient | None:
        """
        Find the best matching ingredient by name using fuzzy matching.
        
        Tries in order:
        1. Exact match (case-insensitive)
        2. Normalized match (removes quantity words, units, prep methods)
        3. Singular/plural match
        4. Substring match (prefers shorter base ingredients)
        
        Returns the best match or None if no good match found.
        """
        from models.ingredient import Ingredient
        
        # Try exact match first (fast - uses index)
        ingredient = get_ingredient_by_name(db, ingredient_name)
        if ingredient:
            return ingredient
        
        # Normalize the input name
        normalized_input = self._normalize_ingredient_name(ingredient_name)
        
        # Try case-insensitive match on normalized input
        exact_match = db.query(Ingredient).filter(
            func.lower(Ingredient.name) == normalized_input
        ).first()
        if exact_match:
            logger.info(f"Matched '{ingredient_name}' to '{exact_match.name}' (case-insensitive)")
            return exact_match
        
        # Get ingredients with similar names (limit to 100 for performance)
        # Use LIKE to filter candidates
        first_word = normalized_input.split()[0] if normalized_input else ''
        if len(first_word) < 3:
            # Too short, don't fuzzy match
            return None
        
        candidates = db.query(Ingredient).filter(
            func.lower(Ingredient.name).like(f'%{first_word}%')
        ).limit(100).all()
        
        if not candidates:
            return None
        
        # Track best matches by priority
        exact_normalized_match = None
        singular_plural_match = None
        substring_matches = []
        
        for ing in candidates:
            normalized_existing = self._normalize_ingredient_name(ing.name)
            
            # Priority 1: Exact normalized match
            if normalized_input == normalized_existing:
                exact_normalized_match = ing
                break
            
            # Priority 2: Singular/plural match
            if (self._to_singular(normalized_input) == self._to_singular(normalized_existing)):
                if not singular_plural_match:
                    singular_plural_match = ing
            
            # Priority 3: Substring match (one contains the other)
            if normalized_input in normalized_existing:
                # Input is shorter - prefer the shorter ingredient (more generic)
                substring_matches.append((ing, len(normalized_existing)))
            elif normalized_existing in normalized_input:
                # Existing is shorter - prefer it
                substring_matches.append((ing, len(normalized_existing)))
        
        # Return best match
        if exact_normalized_match:
            logger.info(f"Fuzzy matched '{ingredient_name}' to '{exact_normalized_match.name}' (normalized)")
            return exact_normalized_match
        
        if singular_plural_match:
            logger.info(f"Fuzzy matched '{ingredient_name}' to '{singular_plural_match.name}' (singular/plural)")
            return singular_plural_match
        
        if substring_matches:
            # Sort by length - prefer shorter (more generic) ingredients
            substring_matches.sort(key=lambda x: x[1])
            best_match = substring_matches[0][0]
            logger.info(f"Fuzzy matched '{ingredient_name}' to '{best_match.name}' (substring)")
            return best_match
        
        return None
    
    def _to_singular(self, word: str) -> str:
        """Convert word to singular form (simple heuristic)."""
        if word.endswith('ies'):
            return word[:-3] + 'y'
        if word.endswith('es'):
            return word[:-2]
        if word.endswith('s') and not word.endswith('ss'):
            return word[:-1]
        return word
    
    def _normalize_ingredient_name(self, name: str) -> str:
        """
        Normalize ingredient name by removing quantity words, units, and prep methods.
        
        Examples:
        - "2 chicken breasts (1 lb)" -> "chicken breasts"
        - "1 cup greek yogurt (8 oz)" -> "greek yogurt"
        - "diced cooked chicken" -> "chicken"
        """
        import re
        
        name = name.lower().strip()
        
        # Remove quantity numbers and fractions at start
        name = re.sub(r'^\d+(\.\d+)?(\s*/\s*\d+)?\s+', '', name)
        
        # Remove units in parentheses
        name = re.sub(r'\s*\([^)]*\)', '', name)
        
        # Remove common prep words
        prep_words = [
            'diced', 'chopped', 'sliced', 'minced', 'grated', 'shredded',
            'cooked', 'raw', 'fresh', 'frozen', 'canned', 'dried',
            'halved', 'quartered', 'whole', 'ground', 'crushed',
            'thinly', 'finely', 'roughly', 'crumbled'
        ]
        for word in prep_words:
            name = re.sub(rf'\b{word}\b\s*', '', name)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name.strip()

    def _add_meal_ingredients_to_list(
        self,
        db: Session,
        grocery_list_id: int,
        items_data: list[dict],
    ) -> int:
        """
        Add meal ingredients to grocery list.
        Uses fuzzy matching to find existing ingredients before creating new ones.
        """
        from models.grocery_list import GroceryListItem

        created_count = 0
        for data in items_data:
            ingredient_name = data.get("ingredient_name", "").strip().lower()
            quantity_text = data.get("quantity_text", "")

            if not ingredient_name:
                continue

            # Try to find best matching ingredient using fuzzy matching
            ingredient = self._find_best_matching_ingredient(db, ingredient_name)
            
            if not ingredient:
                # No match found - create new ingredient
                try:
                    ingredient = create_ingredient(db, name=ingredient_name, category=None)
                    logger.info(f"Created new ingredient: '{ingredient_name}'")
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
    ) -> tuple[int, int, list[dict], GroceryList]:
        """
        ACID-safe pantry sync using canonical units for proper comparison.

        Flow:
        1. Get full grocery list with each item's quantity and unit
        2. Normalize units for each grocery item to canonical units
        3. Get pantry items (family pantry if user is in family, else personal)
        4. Normalize pantry item units to canonical units
        5. Calculate remaining to buy for each grocery list item
        6. Remove fully covered items, reduce partially covered items
        7. Return items_removed, items_updated, remaining_items, and updated list

        Args:
            db: Database session
            grocery_list: Pre-loaded GroceryList with items

        Returns:
            (items_removed, items_updated, remaining_items, updated_grocery_list)
        """
        from datetime import datetime, timezone
        from services.grocery_calculator import get_pantry_totals_flexible, format_for_display, parse_amount_string
        from services.unit_normalizer import try_normalize_quantity
        from crud.ingredients import get_ingredient

        logger.info(f"Syncing list {grocery_list.id} with pantry using flexible unit comparison")

        # Determine pantry scope
        # For personal lists with family membership, sync against family pantry
        # For family lists, sync against family pantry
        family_id = None
        owner_user_id = None

        if grocery_list.owner_user_id is not None:
            # Personal list - check if user has family
            membership = db.query(FamilyMembership).filter(
                FamilyMembership.user_id == grocery_list.owner_user_id
            ).first()
            if membership:
                family_id = membership.family_id
            else:
                owner_user_id = grocery_list.owner_user_id
        else:
            # Family list
            family_id = grocery_list.family_id

        # Get flexible pantry totals (includes both canonical and display quantities)
        pantry_totals = get_pantry_totals_flexible(
            db,
            family_id=family_id,
            owner_user_id=owner_user_id,
        )

        logger.info(f"Found pantry totals for {len(pantry_totals)} ingredients")

        items_removed = 0
        items_updated = 0
        remaining_items = []

        # Process each unchecked item (copy list to allow deletion during iteration)
        for item in list(grocery_list.items):
            if item.checked:
                # Skip checked items - user already marked as purchased
                continue

            ingredient = item.ingredient
            if not ingredient:
                ingredient = get_ingredient(db, item.ingredient_id)

            ingredient_name = ingredient.name if ingredient else f"Ingredient {item.ingredient_id}"

            # Step 2: Get canonical quantity for grocery item
            # Use stored canonical values if available, otherwise try to normalize
            grocery_canonical_qty = item.canonical_quantity_needed
            grocery_canonical_unit = item.canonical_unit
            has_valid_canonical = grocery_canonical_qty is not None and grocery_canonical_qty > 0
            
            # Store original display values for later
            original_display_qty = item.quantity
            original_display_unit = item.unit.code if item.unit else None

            # Try to normalize if we don't have valid canonical values
            if not has_valid_canonical and item.quantity is not None and item.quantity > 0:
                unit_code = item.unit.code if item.unit else None
                if unit_code and ingredient:
                    normalized_qty, normalized_unit = try_normalize_quantity(
                        ingredient, float(item.quantity), unit_code
                    )
                    if normalized_qty is not None and normalized_qty > 0:
                        grocery_canonical_qty = Decimal(str(normalized_qty))
                        grocery_canonical_unit = normalized_unit
                        has_valid_canonical = True
                        # Store the normalized values for future use
                        item.canonical_quantity_needed = grocery_canonical_qty
                        item.canonical_unit = grocery_canonical_unit
                        db.add(item)

            # If still no valid canonical, try to parse from note field (e.g., "2 cups")
            if not has_valid_canonical and item.note:
                parsed_qty, parsed_unit = parse_amount_string(item.note)
                if parsed_qty is not None and parsed_qty > 0 and parsed_unit:
                    # Store original display values from note
                    original_display_qty = Decimal(str(parsed_qty))
                    original_display_unit = parsed_unit
                    
                    # Update item with parsed values (even if normalization fails)
                    item.quantity = original_display_qty
                    db.add(item)
                    
                    # Try to normalize the parsed values
                    if ingredient:
                        normalized_qty, normalized_unit = try_normalize_quantity(
                            ingredient, float(parsed_qty), parsed_unit
                        )
                        if normalized_qty is not None and normalized_qty > 0:
                            grocery_canonical_qty = Decimal(str(normalized_qty))
                            grocery_canonical_unit = normalized_unit
                            has_valid_canonical = True
                            item.canonical_quantity_needed = grocery_canonical_qty
                            item.canonical_unit = grocery_canonical_unit
                            db.add(item)
                            logger.info(
                                f"Parsed and normalized '{item.note}' for {ingredient_name}: "
                                f"{parsed_qty} {parsed_unit} -> {grocery_canonical_qty} {grocery_canonical_unit}"
                            )
                        else:
                            # Normalization failed but we still have parsed display values
                            # Use display values for comparison
                            grocery_canonical_qty = original_display_qty
                            grocery_canonical_unit = parsed_unit
                            has_valid_canonical = True
                            item.canonical_quantity_needed = grocery_canonical_qty
                            item.canonical_unit = grocery_canonical_unit
                            db.add(item)
                            logger.info(
                                f"Parsed '{item.note}' for {ingredient_name}: using display units "
                                f"{parsed_qty} {parsed_unit}"
                            )

            # If still no valid values, add to remaining as-is (can't compare)
            if not has_valid_canonical:
                logger.debug(
                    f"Item {ingredient_name} has no canonical quantity - keeping as remaining "
                    f"(quantity={item.quantity}, note={item.note})"
                )
                remaining_items.append({
                    "ingredient_id": item.ingredient_id,
                    "ingredient_name": ingredient_name,
                    "quantity": item.quantity,
                    "unit_code": item.unit.code if item.unit else None,
                    "canonical_quantity": None,
                    "canonical_unit": None,
                    "note": item.note,
                })
                continue

            # Step 4: Get pantry availability for this ingredient
            pantry_qty = Decimal(0)
            pantry_unit = None
            
            if item.ingredient_id in pantry_totals:
                pantry_data = pantry_totals[item.ingredient_id]
                
                # Try canonical first, then fall back to display
                if pantry_data['canonical_quantity'] and pantry_data['canonical_unit']:
                    pantry_qty = pantry_data['canonical_quantity']
                    pantry_unit = pantry_data['canonical_unit']
                elif pantry_data['display_quantity'] and pantry_data['display_unit']:
                    # Use display quantities for comparison
                    pantry_qty = pantry_data['display_quantity']
                    pantry_unit = pantry_data['display_unit']

            # Step 5: Calculate remaining
            # Compare using matching units (canonical or display)
            if pantry_unit and grocery_canonical_unit and pantry_unit != grocery_canonical_unit:
                # Unit mismatch - log warning and keep item as-is
                logger.warning(
                    f"Canonical unit mismatch for {ingredient_name}: "
                    f"pantry={pantry_unit}, grocery={grocery_canonical_unit}"
                )
                remaining_items.append({
                    "ingredient_id": item.ingredient_id,
                    "ingredient_name": ingredient_name,
                    "quantity": item.quantity,
                    "unit_code": item.unit.code if item.unit else None,
                    "canonical_quantity": grocery_canonical_qty,
                    "canonical_unit": grocery_canonical_unit,
                    "note": item.note,
                })
                continue

            remaining_qty = grocery_canonical_qty - pantry_qty

            # Step 6: Update or remove items
            if remaining_qty <= 0:
                # Fully covered by pantry - remove from grocery list
                db.delete(item)
                items_removed += 1
                logger.info(f"Removed {ingredient_name} - fully covered by pantry (had {grocery_canonical_qty}, pantry has {pantry_qty})")
            elif remaining_qty < grocery_canonical_qty:
                # Partially covered - reduce quantity
                items_updated += 1

                # Update canonical quantity
                item.canonical_quantity_needed = remaining_qty
                item.canonical_unit = grocery_canonical_unit

                # Also update display quantity
                display_qty, display_unit = format_for_display(remaining_qty, grocery_canonical_unit)
                item.quantity = display_qty
                db.add(item)

                # Add to remaining items
                remaining_items.append({
                    "ingredient_id": item.ingredient_id,
                    "ingredient_name": ingredient_name,
                    "quantity": display_qty,
                    "unit_code": display_unit,
                    "canonical_quantity": remaining_qty,
                    "canonical_unit": grocery_canonical_unit,
                    "note": item.note,
                })
                logger.info(
                    f"Updated {ingredient_name}: {grocery_canonical_qty} -> {remaining_qty} {grocery_canonical_unit}"
                )
            else:
                # Not in pantry at all (remaining_qty == grocery_canonical_qty) - keep as-is, add to remaining
                # Use original display values or format from canonical
                if original_display_qty is not None:
                    display_qty = original_display_qty
                    display_unit = original_display_unit or grocery_canonical_unit
                else:
                    display_qty, display_unit = format_for_display(grocery_canonical_qty, grocery_canonical_unit)
                
                remaining_items.append({
                    "ingredient_id": item.ingredient_id,
                    "ingredient_name": ingredient_name,
                    "quantity": display_qty,
                    "unit_code": display_unit,
                    "canonical_quantity": grocery_canonical_qty,
                    "canonical_unit": grocery_canonical_unit,
                    "note": item.note,
                })
                logger.debug(f"Keeping {ingredient_name} as-is - not in pantry")

        # Update timestamp explicitly
        grocery_list.updated_at = datetime.now(timezone.utc)

        # Single commit - ACID transaction
        db.commit()
        db.refresh(grocery_list)

        logger.info(
            f"Sync complete for list {grocery_list.id}: "
            f"{items_removed} removed, {items_updated} updated, "
            f"{len(remaining_items)} items remaining"
        )

        return items_removed, items_updated, remaining_items, grocery_list

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


    def rebuild_grocery_list_from_meal_plan(
        self,
        db: Session,
        meal_plan_id: int,
        user_id: int,
        preserve_purchased: bool = True,
    ) -> GroceryList:
        """
        Rebuild grocery list from meal plan using canonical unit calculations.

        Calculates total ingredient needs from meal plan, subtracts pantry
        availability, and creates grocery list items for remaining needs.

        Phase 3: Preserves manual items (is_manual=True) and optionally
        preserves purchased items. Only deletes auto-generated, unpurchased
        items from this meal plan.

        Args:
            db: Database session
            meal_plan_id: MealPlan to generate list from
            user_id: User requesting the rebuild
            preserve_purchased: If True, don't delete already purchased items

        Returns:
            GroceryList with computed items

        Raises:
            ValueError: If meal plan not found or user lacks access
        """
        from datetime import datetime, timezone
        from models.grocery_list import GroceryListItem
        from models.meal_plan import MealPlan
        from services.grocery_calculator import (
            calculate_total_needed,
            get_pantry_totals,
            compute_remaining_to_buy,
            format_for_display,
            get_unit_id_by_code,
        )
        from crud.ingredients import get_ingredient

        logger.info(
            f"Rebuilding grocery list from meal plan {meal_plan_id} for user {user_id}"
        )

        # Load meal plan
        meal_plan = db.query(MealPlan).filter(MealPlan.id == meal_plan_id).first()
        if not meal_plan:
            raise ValueError(f"MealPlan {meal_plan_id} not found")

        # Determine scope from meal plan
        family_id = meal_plan.family_id
        owner_user_id = meal_plan.owner_user_id

        # Validate user access
        if family_id:
            membership = db.query(FamilyMembership).filter(
                FamilyMembership.family_id == family_id,
                FamilyMembership.user_id == user_id,
            ).first()
            if not membership:
                raise ValueError("User not authorized to access this meal plan")
        elif owner_user_id:
            if owner_user_id != user_id:
                raise ValueError("User not authorized to access this meal plan")

        # Get or create grocery list for this meal plan
        grocery_list = db.query(GroceryList).filter(
            GroceryList.meal_plan_id == meal_plan_id
        ).first()

        # Track which ingredient_ids are already covered by preserved items
        preserved_ingredient_ids: set[int] = set()

        if grocery_list:
            # Phase 3: Delete only auto-generated, unpurchased items from this meal plan
            # Preserve: manual items (is_manual=True) and purchased items (is_purchased=True)
            items_to_delete = []
            for item in grocery_list.items:
                should_preserve = item.is_manual or (preserve_purchased and item.is_purchased)
                is_from_this_plan = item.source_meal_plan_id == meal_plan_id
                
                if is_from_this_plan and not should_preserve:
                    items_to_delete.append(item)
                elif should_preserve:
                    # Track preserved items so we don't duplicate them
                    preserved_ingredient_ids.add(item.ingredient_id)
            
            for item in items_to_delete:
                db.delete(item)
            db.flush()
            
            logger.info(
                f"Cleared {len(items_to_delete)} auto-generated items from grocery list {grocery_list.id} "
                f"(preserved {len(preserved_ingredient_ids)} manual/purchased items)"
            )
        else:
            # Create new grocery list
            grocery_list = create_grocery_list(
                db,
                family_id=family_id,
                owner_user_id=owner_user_id,
                title=f"Shopping list for {meal_plan.title or 'Meal Plan'}",
                status="draft",
                meal_plan_id=meal_plan_id,
                created_by_user_id=user_id,
            )
            logger.info(f"Created new grocery list {grocery_list.id}")

        # Calculate total canonical needs from meal plan
        try:
            total_needed = calculate_total_needed(db, meal_plan_id)
        except ValueError as e:
            logger.error(f"Error calculating needs: {e}")
            raise
        except Exception as e:
            # Safety: catch any unexpected errors during calculation
            logger.error(f"Unexpected error calculating needs: {e}")
            total_needed = {}

        if not total_needed:
            logger.info("No ingredients found in meal plan")
            grocery_list.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(grocery_list)
            return grocery_list

        # Get pantry totals based on scope
        pantry_totals = get_pantry_totals(
            db,
            family_id=family_id,
            owner_user_id=owner_user_id,
        )

        # Compute remaining to buy
        remaining = compute_remaining_to_buy(total_needed, pantry_totals)

        logger.info(
            f"Computed needs: {len(total_needed)} total, "
            f"{len(pantry_totals)} in pantry, {len(remaining)} remaining"
        )

        # Create grocery list items for remaining needs
        items_created = 0
        items_skipped = 0
        
        for ingredient_id, (canonical_qty, canonical_unit) in remaining.items():
            # Skip if ingredient is already covered by a preserved item
            if ingredient_id in preserved_ingredient_ids:
                items_skipped += 1
                logger.debug(f"Skipping ingredient {ingredient_id} - already has preserved item")
                continue

            # Safety: skip if canonical data is invalid
            if canonical_qty is None or canonical_qty <= 0:
                logger.warning(f"Skipping ingredient {ingredient_id} - invalid canonical quantity")
                continue
            
            if not canonical_unit:
                logger.warning(f"Skipping ingredient {ingredient_id} - missing canonical unit")
                continue

            try:
                # Format for display
                display_qty, display_unit = format_for_display(canonical_qty, canonical_unit)

                # Get unit ID for display unit
                unit_id = get_unit_id_by_code(db, display_unit)

                # Get ingredient for logging
                ingredient = get_ingredient(db, ingredient_id)
                ingredient_name = ingredient.name if ingredient else f"ID:{ingredient_id}"

                # Phase 3: Create grocery list item with tracking fields
                new_item = GroceryListItem(
                    grocery_list_id=grocery_list.id,
                    ingredient_id=ingredient_id,
                    quantity=display_qty,
                    unit_id=unit_id,
                    canonical_quantity_needed=canonical_qty,
                    canonical_unit=canonical_unit,
                    checked=False,
                    is_purchased=False,
                    is_manual=False,
                    source_meal_plan_id=meal_plan_id,
                )
                db.add(new_item)
                items_created += 1

                logger.debug(
                    f"Added {ingredient_name}: {display_qty} {display_unit} "
                    f"(canonical: {canonical_qty} {canonical_unit})"
                )
            except Exception as e:
                logger.error(f"Failed to create item for ingredient {ingredient_id}: {e}")
                continue

        # Update timestamp
        grocery_list.updated_at = datetime.now(timezone.utc)

        # Commit all changes
        db.commit()
        db.refresh(grocery_list)

        logger.info(
            f"Rebuilt grocery list {grocery_list.id} with {items_created} new items "
            f"({items_skipped} skipped due to preserved items)"
        )

        return grocery_list

    def mark_item_purchased(
        self,
        db: Session,
        grocery_list_item_id: int,
        user_id: int,
    ) -> tuple["GroceryListItem", "PantryItem"]:
        """
        Mark a grocery list item as purchased and add quantity to pantry.

        When the user marks an item as purchased:
        1. Set is_purchased = True on the grocery item
        2. Find or create a PantryItem for the same ingredient
        3. Add the canonical quantity to the pantry

        Args:
            db: Database session
            grocery_list_item_id: The grocery list item to mark as purchased
            user_id: User performing the action

        Returns:
            Tuple of (updated GroceryListItem, updated/created PantryItem)

        Raises:
            ValueError: If item not found or user lacks access
        """
        from datetime import datetime, timezone
        from models.grocery_list import GroceryListItem
        from models.pantry_item import PantryItem
        from crud.grocery_lists import get_grocery_list

        logger.info(f"Marking grocery item {grocery_list_item_id} as purchased by user {user_id}")

        # Fetch the grocery list item
        item = db.query(GroceryListItem).filter(
            GroceryListItem.id == grocery_list_item_id
        ).first()

        if not item:
            raise ValueError(f"GroceryListItem {grocery_list_item_id} not found")

        # Fetch the grocery list to validate access
        grocery_list = get_grocery_list(db, item.grocery_list_id)
        if not grocery_list:
            raise ValueError("Grocery list not found")

        # Validate user access
        if not self.validate_list_access(db, grocery_list, user_id):
            raise ValueError("User not authorized to access this grocery list")

        # Check if already purchased
        if item.is_purchased:
            logger.info(f"Item {grocery_list_item_id} is already marked as purchased")
            # Still return the item and find the pantry item
            pantry_item = self._find_pantry_item_for_ingredient(
                db, item.ingredient_id, grocery_list, user_id
            )
            return item, pantry_item

        # Mark as purchased
        item.is_purchased = True
        item.checked = True  # Also check off the item
        db.add(item)

        # Add quantity to pantry
        pantry_item = self._add_purchased_to_pantry(
            db, item, grocery_list, user_id
        )

        db.commit()
        db.refresh(item)
        db.refresh(pantry_item)

        logger.info(
            f"Marked item {grocery_list_item_id} as purchased, "
            f"added {item.canonical_quantity_needed} {item.canonical_unit} to pantry"
        )

        return item, pantry_item

    def _find_pantry_item_for_ingredient(
        self,
        db: Session,
        ingredient_id: int,
        grocery_list: GroceryList,
        user_id: int,
    ) -> Optional["PantryItem"]:
        """Find existing pantry item for an ingredient based on grocery list scope."""
        from models.pantry_item import PantryItem

        if grocery_list.family_id:
            # Family list -> family pantry
            return db.query(PantryItem).filter(
                PantryItem.family_id == grocery_list.family_id,
                PantryItem.ingredient_id == ingredient_id,
            ).first()
        else:
            # Personal list -> personal pantry
            return db.query(PantryItem).filter(
                PantryItem.owner_user_id == user_id,
                PantryItem.ingredient_id == ingredient_id,
            ).first()

    def _add_purchased_to_pantry(
        self,
        db: Session,
        item: "GroceryListItem",
        grocery_list: GroceryList,
        user_id: int,
    ) -> "PantryItem":
        """
        Add purchased grocery item quantity to pantry.

        Creates a new pantry item if one doesn't exist for this ingredient.
        """
        from models.pantry_item import PantryItem
        from models.ingredient import Ingredient

        # Determine pantry scope from grocery list
        family_id = grocery_list.family_id
        owner_user_id = user_id if grocery_list.owner_user_id else None

        # Find existing pantry item for this ingredient
        pantry_item = self._find_pantry_item_for_ingredient(
            db, item.ingredient_id, grocery_list, user_id
        )

        # Get the canonical quantity to add
        qty_to_add = item.canonical_quantity_needed or Decimal(0)
        canonical_unit = item.canonical_unit

        if pantry_item:
            # Update existing pantry item
            current_qty = pantry_item.canonical_quantity or Decimal(0)

            # Verify units match (they should if both are canonical)
            if pantry_item.canonical_unit and pantry_item.canonical_unit != canonical_unit:
                logger.warning(
                    f"Canonical unit mismatch for ingredient {item.ingredient_id}: "
                    f"pantry has {pantry_item.canonical_unit}, grocery has {canonical_unit}"
                )
                # Still add, but log warning

            pantry_item.canonical_quantity = current_qty + qty_to_add

            # Also update display quantity if we have it
            if item.quantity and item.unit_id:
                display_qty = pantry_item.quantity or Decimal(0)
                pantry_item.quantity = display_qty + item.quantity

            db.add(pantry_item)
            logger.debug(
                f"Updated pantry item {pantry_item.id}: "
                f"added {qty_to_add} {canonical_unit}"
            )
        else:
            # Create new pantry item
            ingredient = db.query(Ingredient).filter(
                Ingredient.id == item.ingredient_id
            ).first()

            pantry_item = PantryItem(
                family_id=family_id,
                owner_user_id=owner_user_id,
                ingredient_id=item.ingredient_id,
                quantity=item.quantity,  # Display quantity
                unit=None,  # We'll use unit_id lookup if needed
                canonical_quantity=qty_to_add,
                canonical_unit=canonical_unit or (ingredient.canonical_unit if ingredient else None),
                category=ingredient.category if ingredient else None,
            )
            db.add(pantry_item)
            logger.debug(
                f"Created new pantry item for ingredient {item.ingredient_id}: "
                f"{qty_to_add} {canonical_unit}"
            )

        return pantry_item

    def recompute_grocery_list_for_user(
        self,
        db: Session,
        user_id: int,
    ) -> list[GroceryList]:
        """
        Recompute all grocery lists for a user after pantry changes.

        For each meal plan belonging to the user that has an active grocery list,
        rebuild the grocery list while preserving manual items.

        Args:
            db: Database session
            user_id: User whose grocery lists should be recomputed

        Returns:
            List of updated grocery lists
        """
        from models.meal_plan import MealPlan
        from models.membership import FamilyMembership

        logger.info(f"Recomputing grocery lists for user {user_id}")

        updated_lists = []

        # Get user's family memberships
        memberships = db.query(FamilyMembership).filter(
            FamilyMembership.user_id == user_id
        ).all()
        family_ids = [m.family_id for m in memberships]

        # Find meal plans that belong to user (personal or family)
        meal_plans_query = db.query(MealPlan).filter(
            MealPlan.created_by_user_id == user_id
        )

        # Also include family meal plans
        if family_ids:
            from sqlalchemy import or_
            meal_plans_query = db.query(MealPlan).filter(
                or_(
                    MealPlan.created_by_user_id == user_id,
                    MealPlan.family_id.in_(family_ids)
                )
            )

        meal_plans = meal_plans_query.all()

        for meal_plan in meal_plans:
            # Check if this meal plan has an associated grocery list
            grocery_list = db.query(GroceryList).filter(
                GroceryList.meal_plan_id == meal_plan.id,
                GroceryList.status != "purchased"  # Don't update completed lists
            ).first()

            if grocery_list:
                try:
                    updated_list = self.rebuild_grocery_list_from_meal_plan(
                        db,
                        meal_plan_id=meal_plan.id,
                        user_id=user_id,
                    )
                    updated_lists.append(updated_list)
                    logger.info(f"Recomputed grocery list {updated_list.id} for meal plan {meal_plan.id}")
                except Exception as e:
                    logger.error(f"Failed to recompute grocery list for meal plan {meal_plan.id}: {e}")
                    # Continue with other lists

        logger.info(f"Recomputed {len(updated_lists)} grocery lists for user {user_id}")
        return updated_lists

    def debug_meal_plan_requirements(
        self,
        db: Session,
        meal_plan_id: int,
        user_id: int,
    ) -> dict:
        """
        Debug helper to inspect meal plan requirements and pantry availability.

        Returns detailed breakdown of:
        - Total ingredients needed from meal plan
        - Current pantry availability
        - Remaining to buy

        Args:
            db: Database session
            meal_plan_id: MealPlan to debug
            user_id: User requesting the debug info

        Returns:
            Dict with debug information per ingredient

        Raises:
            ValueError: If meal plan not found or user lacks access
        """
        from models.meal_plan import MealPlan
        from services.grocery_calculator import (
            calculate_total_needed,
            get_pantry_totals,
            compute_remaining_to_buy,
        )
        from crud.ingredients import get_ingredient

        logger.info(f"Debug: Analyzing meal plan {meal_plan_id} for user {user_id}")

        # Load meal plan
        meal_plan = db.query(MealPlan).filter(MealPlan.id == meal_plan_id).first()
        if not meal_plan:
            raise ValueError(f"MealPlan {meal_plan_id} not found")

        # Validate user access
        family_id = meal_plan.family_id
        owner_user_id = meal_plan.owner_user_id

        if family_id:
            membership = db.query(FamilyMembership).filter(
                FamilyMembership.family_id == family_id,
                FamilyMembership.user_id == user_id,
            ).first()
            if not membership:
                raise ValueError("User not authorized to access this meal plan")
        elif owner_user_id:
            if owner_user_id != user_id:
                raise ValueError("User not authorized to access this meal plan")

        # Calculate all values
        try:
            total_needed = calculate_total_needed(db, meal_plan_id)
        except Exception as e:
            logger.error(f"Error calculating needs: {e}")
            total_needed = {}

        pantry_totals = get_pantry_totals(
            db,
            family_id=family_id,
            owner_user_id=owner_user_id,
        )

        remaining = compute_remaining_to_buy(total_needed, pantry_totals)

        # Build detailed response
        ingredients_detail = []
        all_ingredient_ids = set(total_needed.keys()) | set(pantry_totals.keys())

        for ing_id in all_ingredient_ids:
            ingredient = get_ingredient(db, ing_id)
            ingredient_name = ingredient.name if ingredient else f"Unknown (ID: {ing_id})"

            needed_qty, needed_unit = total_needed.get(ing_id, (Decimal(0), None))
            avail_qty, avail_unit = pantry_totals.get(ing_id, (Decimal(0), None))
            remain_qty, remain_unit = remaining.get(ing_id, (Decimal(0), None))

            ingredients_detail.append({
                "ingredient_id": ing_id,
                "ingredient_name": ingredient_name,
                "canonical_unit": needed_unit or avail_unit or remain_unit,
                "needed": float(needed_qty) if needed_qty else 0,
                "available_in_pantry": float(avail_qty) if avail_qty else 0,
                "remaining_to_buy": float(remain_qty) if remain_qty else 0,
                "is_fully_covered": ing_id not in remaining,
            })

        # Sort by name for easier reading
        ingredients_detail.sort(key=lambda x: x["ingredient_name"].lower())

        return {
            "meal_plan_id": meal_plan_id,
            "meal_plan_title": meal_plan.title,
            "scope": "family" if family_id else "personal",
            "family_id": family_id,
            "owner_user_id": owner_user_id,
            "summary": {
                "total_ingredients_needed": len(total_needed),
                "ingredients_in_pantry": len(pantry_totals),
                "ingredients_to_buy": len(remaining),
                "fully_covered_count": len(total_needed) - len(remaining),
            },
            "ingredients": ingredients_detail,
        }


# Singleton instance
grocery_list_service = GroceryListService()
