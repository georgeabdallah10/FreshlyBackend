# services/grocery_calculator.py
"""
Grocery Calculator Service

Phase 2 of unit normalization: Calculate grocery list needs from meal plans
by comparing canonical quantities needed vs pantry availability.
"""
import logging
import re
import math
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.meal_plan import MealPlan, MealSlot, MealSlotMeal
from models.meal import Meal
from models.pantry_item import PantryItem
from models.ingredient import Ingredient
from models.unit import Unit
from crud.ingredients import get_ingredient_by_name, create_ingredient
from services.unit_normalizer import try_normalize_quantity
from core.unit_conversions import WEIGHT_CONVERSIONS, VOLUME_CONVERSIONS, COUNT_UNITS

logger = logging.getLogger(__name__)


def calculate_total_needed(
    db: Session,
    meal_plan_id: int,
) -> dict[int, tuple[Decimal, str]]:
    """
    Calculate total canonical ingredient requirements for a meal plan.

    Loops through all meals in the plan, parses their ingredients,
    normalizes quantities, and sums totals per ingredient_id.

    Args:
        db: Database session
        meal_plan_id: MealPlan to calculate needs for

    Returns:
        Dict mapping ingredient_id -> (canonical_quantity_total, canonical_unit)
    """
    logger.info(f"Calculating total needs for meal plan {meal_plan_id}")

    # Load meal plan with all nested relationships
    meal_plan = db.query(MealPlan).filter(MealPlan.id == meal_plan_id).first()
    if not meal_plan:
        raise ValueError(f"MealPlan {meal_plan_id} not found")

    # Dict to accumulate: ingredient_id -> (total_qty, canonical_unit)
    totals: dict[int, tuple[Decimal, str]] = {}

    # Traverse: MealPlan → MealSlot → MealSlotMeal → Meal → ingredients (JSONB)
    for slot in meal_plan.slots:
        # Use slot.servings as multiplier if set, otherwise default to 1
        slot_servings = slot.servings or 1

        for meal_slot_meal in slot.meals:
            # Use portions from MealSlotMeal if set, otherwise 1
            portions = meal_slot_meal.portions or 1
            multiplier = slot_servings * portions

            meal = meal_slot_meal.meal
            if not meal:
                continue

            # Parse JSONB ingredients: [{"name": "flour", "amount": "2 cups"}, ...]
            meal_ingredients = meal.ingredients or []

            for ingredient_data in meal_ingredients:
                name = ingredient_data.get("name", "").strip()
                amount_str = ingredient_data.get("amount", "")

                if not name:
                    continue

                # Look up or create ingredient
                ingredient = get_ingredient_by_name(db, name)
                if not ingredient:
                    try:
                        ingredient = create_ingredient(db, name=name, category=None)
                    except Exception as e:
                        logger.warning(f"Failed to create ingredient '{name}': {e}")
                        continue

                # Parse amount string to get quantity and unit
                qty, unit = parse_amount_string(amount_str)
                if qty is None or unit is None:
                    # Can't parse - skip or store raw
                    logger.debug(f"Could not parse amount '{amount_str}' for {name}")
                    continue

                # Apply multiplier
                qty = qty * multiplier

                # Normalize to canonical unit
                canonical_qty, canonical_unit = try_normalize_quantity(
                    ingredient, float(qty), unit
                )

                if canonical_qty is None or canonical_unit is None:
                    # Normalization failed - ingredient missing canonical metadata
                    logger.debug(
                        f"Could not normalize {qty} {unit} of {name} - "
                        f"ingredient missing canonical unit metadata"
                    )
                    continue

                # Accumulate
                ing_id = ingredient.id
                if ing_id in totals:
                    existing_qty, existing_unit = totals[ing_id]
                    # Quantities should be in same canonical unit
                    if existing_unit == canonical_unit:
                        totals[ing_id] = (
                            existing_qty + Decimal(str(canonical_qty)),
                            canonical_unit,
                        )
                    else:
                        # Unit mismatch - shouldn't happen if canonical is consistent
                        logger.warning(
                            f"Canonical unit mismatch for ingredient {ing_id}: "
                            f"{existing_unit} vs {canonical_unit}"
                        )
                else:
                    totals[ing_id] = (Decimal(str(canonical_qty)), canonical_unit)

    logger.info(f"Calculated needs for {len(totals)} ingredients")
    return totals


def get_pantry_totals(
    db: Session,
    family_id: int | None = None,
    owner_user_id: int | None = None,
) -> dict[int, tuple[Decimal, str]]:
    """
    Get pantry inventory totals grouped by ingredient_id using canonical quantities.

    Args:
        db: Database session
        family_id: Family scope (optional)
        owner_user_id: User scope for personal pantry (optional)

    Returns:
        Dict mapping ingredient_id -> (canonical_quantity_total, canonical_unit)
    """
    logger.info(f"Getting pantry totals for family={family_id}, user={owner_user_id}")

    query = db.query(PantryItem).filter(
        PantryItem.canonical_quantity.isnot(None),
        PantryItem.canonical_unit.isnot(None),
    )

    if family_id is not None:
        query = query.filter(PantryItem.family_id == family_id)
    elif owner_user_id is not None:
        query = query.filter(PantryItem.owner_user_id == owner_user_id)

    items = query.all()

    # Aggregate by ingredient_id
    totals: dict[int, tuple[Decimal, str]] = {}

    for item in items:
        if item.ingredient_id is None:
            continue

        ing_id = item.ingredient_id
        qty = item.canonical_quantity
        unit = item.canonical_unit

        if ing_id in totals:
            existing_qty, existing_unit = totals[ing_id]
            if existing_unit == unit:
                totals[ing_id] = (existing_qty + qty, unit)
            else:
                logger.warning(
                    f"Canonical unit mismatch in pantry for ingredient {ing_id}"
                )
        else:
            totals[ing_id] = (qty, unit)

    logger.info(f"Found pantry totals for {len(totals)} ingredients")
    return totals


def get_pantry_totals_flexible(
    db: Session,
    family_id: int | None = None,
    owner_user_id: int | None = None,
) -> dict[int, dict]:
    """
    Get pantry inventory totals with both canonical and display quantities.
    
    This is a more flexible version that includes items even without canonical
    quantities, allowing comparison using display units when canonical aren't available.

    Args:
        db: Database session
        family_id: Family scope (optional)
        owner_user_id: User scope for personal pantry (optional)

    Returns:
        Dict mapping ingredient_id -> {
            'canonical_quantity': Decimal | None,
            'canonical_unit': str | None,
            'display_quantity': Decimal | None,
            'display_unit': str | None,
        }
    """
    logger.info(f"Getting flexible pantry totals for family={family_id}, user={owner_user_id}")

    query = db.query(PantryItem)

    if family_id is not None:
        query = query.filter(PantryItem.family_id == family_id)
    elif owner_user_id is not None:
        query = query.filter(PantryItem.owner_user_id == owner_user_id)

    items = query.all()

    # Aggregate by ingredient_id
    totals: dict[int, dict] = {}

    for item in items:
        if item.ingredient_id is None:
            continue

        ing_id = item.ingredient_id

        if ing_id not in totals:
            totals[ing_id] = {
                'canonical_quantity': Decimal(0),
                'canonical_unit': None,
                'display_quantity': Decimal(0),
                'display_unit': None,
            }

        # Add canonical quantities if available
        if item.canonical_quantity is not None and item.canonical_unit:
            if totals[ing_id]['canonical_unit'] is None:
                totals[ing_id]['canonical_unit'] = item.canonical_unit
            if totals[ing_id]['canonical_unit'] == item.canonical_unit:
                totals[ing_id]['canonical_quantity'] += item.canonical_quantity

        # Add display quantities
        if item.quantity is not None:
            display_unit = item.unit or 'count'
            if totals[ing_id]['display_unit'] is None:
                totals[ing_id]['display_unit'] = display_unit
            if totals[ing_id]['display_unit'] == display_unit:
                totals[ing_id]['display_quantity'] += item.quantity

    logger.info(f"Found flexible pantry totals for {len(totals)} ingredients")
    return totals


def compute_remaining_to_buy(
    needed: dict[int, tuple[Decimal, str]],
    available: dict[int, tuple[Decimal, str]],
) -> dict[int, tuple[Decimal, str]]:
    """
    Calculate remaining quantities to buy.

    For each ingredient in needed, subtract pantry availability.
    remaining = max(needed - available, 0)

    Args:
        needed: Dict from calculate_total_needed()
        available: Dict from get_pantry_totals()

    Returns:
        Dict mapping ingredient_id -> (remaining_canonical_qty, canonical_unit)
        Only includes items where remaining > 0
    """
    remaining: dict[int, tuple[Decimal, str]] = {}

    for ing_id, (needed_qty, needed_unit) in needed.items():
        if ing_id in available:
            avail_qty, avail_unit = available[ing_id]

            # Units should match (both canonical)
            if avail_unit != needed_unit:
                logger.warning(
                    f"Unit mismatch for ingredient {ing_id}: "
                    f"needed {needed_unit}, available {avail_unit}"
                )
                # Use needed value as-is
                remaining[ing_id] = (needed_qty, needed_unit)
            else:
                diff = needed_qty - avail_qty
                if diff > 0:
                    remaining[ing_id] = (diff, needed_unit)
        else:
            # Not in pantry at all - need full amount
            remaining[ing_id] = (needed_qty, needed_unit)

    logger.info(f"Computed {len(remaining)} items remaining to buy")
    return remaining


def format_for_display(
    canonical_qty: Decimal | float,
    canonical_unit: str,
) -> tuple[Decimal, str]:
    """
    Convert canonical quantity to user-friendly display units.

    Rules:
    - If g and qty >= 1000: convert to kg
    - If ml and qty >= 1000: convert to L
    - If count: round up (ceil), use "pcs"

    Args:
        canonical_qty: Quantity in canonical unit
        canonical_unit: Canonical unit code (g, ml, count)

    Returns:
        (display_quantity, display_unit)
    """
    qty = float(canonical_qty)

    if canonical_unit == "g":
        if qty >= 1000:
            return Decimal(str(round(qty / 1000, 2))), "kg"
        else:
            return Decimal(str(round(qty, 1))), "g"

    elif canonical_unit == "ml":
        if qty >= 1000:
            return Decimal(str(round(qty / 1000, 2))), "L"
        else:
            return Decimal(str(round(qty, 1))), "ml"

    elif canonical_unit == "count":
        # Round up for count items
        return Decimal(str(math.ceil(qty))), "pcs"

    else:
        # Unknown unit - return as-is
        return Decimal(str(round(qty, 2))), canonical_unit


def parse_amount_string(amount_str: str) -> tuple[float | None, str | None]:
    """
    Parse an amount string like "2 cups" or "500g" into (quantity, unit).

    Handles formats:
    - "2 cups"
    - "500g"
    - "1.5 kg"
    - "3"
    - "1/2 cup"

    Returns:
        (quantity, unit) or (None, None) if parsing fails
    """
    if not amount_str:
        return None, None

    amount_str = amount_str.strip().lower()

    # Handle fractions like "1/2"
    fraction_match = re.match(r'^(\d+)/(\d+)\s*(.*)$', amount_str)
    if fraction_match:
        numerator = int(fraction_match.group(1))
        denominator = int(fraction_match.group(2))
        
        # Validate denominator to prevent division by zero
        if denominator == 0:
            logger.warning(f"Invalid fraction with zero denominator: {amount_str}")
            return None, None
        
        qty = numerator / denominator
        unit = fraction_match.group(3).strip() or "count"
        return qty, unit

    # Handle "2 cups", "500 g", "1.5kg"
    match = re.match(r'^([\d.]+)\s*(.*)$', amount_str)
    if match:
        try:
            qty = float(match.group(1))
            unit = match.group(2).strip()

            # Normalize common unit variations
            unit = normalize_unit_string(unit)

            if not unit:
                unit = "count"

            return qty, unit
        except ValueError:
            return None, None

    # Can't parse
    return None, None


def normalize_unit_string(unit: str) -> str:
    """
    Normalize unit string variations to standard codes.

    E.g., "cups" -> "cup", "grams" -> "g", "tablespoons" -> "tbsp"
    """
    unit = unit.lower().strip()

    # Weight variations
    weight_map = {
        "gram": "g", "grams": "g", "gr": "g",
        "kilogram": "kg", "kilograms": "kg", "kgs": "kg",
        "pound": "lb", "pounds": "lb", "lbs": "lb",
        "ounce": "oz", "ounces": "oz",
    }

    # Volume variations
    volume_map = {
        "milliliter": "ml", "milliliters": "ml", "mls": "ml",
        "liter": "l", "liters": "l", "litre": "l", "litres": "l",
        "cup": "cup", "cups": "cup",
        "tablespoon": "tbsp", "tablespoons": "tbsp", "tbs": "tbsp", "tb": "tbsp",
        "teaspoon": "tsp", "teaspoons": "tsp", "ts": "tsp",
    }

    # Count variations
    count_map = {
        "piece": "count", "pieces": "count", "pcs": "count", "pc": "count",
        "unit": "count", "units": "count",
        "each": "count", "ea": "count",
        "whole": "count",
    }

    # Check each map
    if unit in weight_map:
        return weight_map[unit]
    if unit in volume_map:
        return volume_map[unit]
    if unit in count_map:
        return count_map[unit]

    # Check if already a standard unit
    if unit in WEIGHT_CONVERSIONS or unit in VOLUME_CONVERSIONS or unit in COUNT_UNITS:
        return unit

    return unit


def get_unit_id_by_code(db: Session, unit_code: str) -> int | None:
    """
    Look up unit ID by code.

    Args:
        db: Database session
        unit_code: Unit code like "g", "kg", "cup"

    Returns:
        Unit ID or None if not found
    """
    unit = db.query(Unit).filter(Unit.code == unit_code).first()
    return unit.id if unit else None
