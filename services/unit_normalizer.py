# services/unit_normalizer.py
"""
Unit normalization service for converting ingredient quantities to canonical units.

This module provides functions to normalize quantities from various units
(weight, volume, count) to an ingredient's canonical unit for accurate
comparison across recipes, pantry items, and grocery lists.
"""
import logging
from typing import TYPE_CHECKING

from core.unit_conversions import (
    WEIGHT_CONVERSIONS,
    VOLUME_CONVERSIONS,
    COUNT_UNITS,
    get_unit_type,
    convert_to_base_unit,
)

if TYPE_CHECKING:
    from models.ingredient import Ingredient

logger = logging.getLogger(__name__)


def normalize_quantity(
    ingredient: "Ingredient",
    quantity: float,
    unit: str,
) -> tuple[float, str]:
    """
    Convert (quantity, unit) to the ingredient's canonical unit.

    Conversion Rules:
    - Weight units → grams using WEIGHT_CONVERSIONS
    - Volume units → ml using VOLUME_CONVERSIONS
    - Count → treated as raw number

    Then convert to the ingredient's canonical unit:
    - If canonical is "count": grams → count using avg_weight_per_unit_g
    - If canonical is "g": ml → g using density_g_per_ml
    - If canonical is "ml": g → ml using density_g_per_ml

    Args:
        ingredient: The Ingredient model with canonical unit metadata
        quantity: The quantity to normalize
        unit: The source unit code (e.g., 'kg', 'cup', 'piece')

    Returns:
        Tuple of (canonical_quantity, canonical_unit)

    Raises:
        ValueError: If conversion cannot be performed due to:
            - Unknown unit
            - Missing density (for volume↔weight conversion)
            - Missing avg_weight_per_unit_g (for weight↔count conversion)
            - Ingredient has no canonical_unit defined
    """
    if not unit:
        raise ValueError("Unit cannot be empty")

    if quantity is None or quantity < 0:
        raise ValueError("Quantity must be a non-negative number")

    # Get ingredient's canonical unit info
    canonical_unit = ingredient.canonical_unit
    canonical_unit_type = ingredient.canonical_unit_type

    # If ingredient has no canonical unit defined, return as-is with a warning
    if not canonical_unit or not canonical_unit_type:
        logger.warning(
            f"Ingredient {ingredient.id} ({ingredient.name}) has no canonical unit defined. "
            f"Returning original quantity and unit."
        )
        return quantity, unit

    # Step 1: Convert input to base unit (g, ml, or count)
    unit_lower = unit.lower().strip()
    input_type = get_unit_type(unit_lower)

    if input_type is None:
        raise ValueError(f"Unknown unit: {unit}")

    base_quantity, base_unit = convert_to_base_unit(quantity, unit_lower)

    # Step 2: Convert base unit to ingredient's canonical unit
    canonical_type_str = (
        canonical_unit_type.value
        if hasattr(canonical_unit_type, "value")
        else str(canonical_unit_type)
    )

    # Same type - just return the base quantity in canonical unit
    if input_type == canonical_type_str:
        return base_quantity, canonical_unit

    # Different types - need conversion using ingredient metadata
    result_quantity = _convert_between_types(
        ingredient=ingredient,
        quantity=base_quantity,
        from_type=input_type,
        to_type=canonical_type_str,
    )

    return result_quantity, canonical_unit


def _convert_between_types(
    ingredient: "Ingredient",
    quantity: float,
    from_type: str,
    to_type: str,
) -> float:
    """
    Convert quantity between different unit types using ingredient metadata.

    Args:
        ingredient: Ingredient with conversion metadata
        quantity: Quantity in base unit of from_type (g, ml, or count)
        from_type: Source type ('weight', 'volume', 'count')
        to_type: Target type ('weight', 'volume', 'count')

    Returns:
        Converted quantity

    Raises:
        ValueError: If conversion is not possible
    """
    density = ingredient.density_g_per_ml
    avg_weight = ingredient.avg_weight_per_unit_g

    # Weight (g) → Volume (ml)
    if from_type == "weight" and to_type == "volume":
        if not density:
            raise ValueError(
                f"Cannot convert weight to volume for '{ingredient.name}': "
                f"density_g_per_ml is not set"
            )
        return quantity / density

    # Volume (ml) → Weight (g)
    if from_type == "volume" and to_type == "weight":
        if not density:
            raise ValueError(
                f"Cannot convert volume to weight for '{ingredient.name}': "
                f"density_g_per_ml is not set"
            )
        return quantity * density

    # Weight (g) → Count
    if from_type == "weight" and to_type == "count":
        if not avg_weight:
            raise ValueError(
                f"Cannot convert weight to count for '{ingredient.name}': "
                f"avg_weight_per_unit_g is not set"
            )
        return quantity / avg_weight

    # Count → Weight (g)
    if from_type == "count" and to_type == "weight":
        if not avg_weight:
            raise ValueError(
                f"Cannot convert count to weight for '{ingredient.name}': "
                f"avg_weight_per_unit_g is not set"
            )
        return quantity * avg_weight

    # Volume (ml) → Count (via weight)
    if from_type == "volume" and to_type == "count":
        if not density:
            raise ValueError(
                f"Cannot convert volume to count for '{ingredient.name}': "
                f"density_g_per_ml is not set"
            )
        if not avg_weight:
            raise ValueError(
                f"Cannot convert volume to count for '{ingredient.name}': "
                f"avg_weight_per_unit_g is not set"
            )
        # ml → g → count
        weight_g = quantity * density
        return weight_g / avg_weight

    # Count → Volume (ml) (via weight)
    if from_type == "count" and to_type == "volume":
        if not avg_weight:
            raise ValueError(
                f"Cannot convert count to volume for '{ingredient.name}': "
                f"avg_weight_per_unit_g is not set"
            )
        if not density:
            raise ValueError(
                f"Cannot convert count to volume for '{ingredient.name}': "
                f"density_g_per_ml is not set"
            )
        # count → g → ml
        weight_g = quantity * avg_weight
        return weight_g / density

    raise ValueError(
        f"Unsupported conversion from {from_type} to {to_type} for '{ingredient.name}'"
    )


def try_normalize_quantity(
    ingredient: "Ingredient",
    quantity: float | None,
    unit: str | None,
) -> tuple[float | None, str | None]:
    """
    Attempt to normalize quantity, returning None values on failure.

    This is a safe wrapper around normalize_quantity that doesn't raise
    exceptions. Useful for batch operations where some items may fail.

    Args:
        ingredient: The Ingredient model
        quantity: The quantity to normalize (may be None)
        unit: The source unit code (may be None)

    Returns:
        Tuple of (canonical_quantity, canonical_unit) or (None, None) on failure
    """
    if quantity is None or unit is None:
        return None, None

    try:
        return normalize_quantity(ingredient, quantity, unit)
    except ValueError as e:
        logger.warning(f"Failed to normalize quantity: {e}")
        return None, None
