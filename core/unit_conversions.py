# core/unit_conversions.py
"""
Unit conversion constants for normalizing ingredient quantities.

All weight units convert to grams (g).
All volume units convert to milliliters (ml).
"""

# Weight conversions to grams
WEIGHT_CONVERSIONS: dict[str, float] = {
    "g": 1.0,
    "kg": 1000.0,
    "lb": 453.592,
    "oz": 28.3495,
}

# Volume conversions to milliliters
VOLUME_CONVERSIONS: dict[str, float] = {
    "ml": 1.0,
    "l": 1000.0,
    "cup": 240.0,
    "tbsp": 15.0,
    "tsp": 5.0,
}

# Count units (no conversion needed)
COUNT_UNITS: set[str] = {
    "count",
    "piece",
    "pieces",
    "unit",
    "units",
    "each",
    "ea",
}


def get_unit_type(unit: str) -> str | None:
    """
    Determine the type of a unit.

    Args:
        unit: The unit code (e.g., 'g', 'ml', 'cup')

    Returns:
        'weight', 'volume', 'count', or None if unknown
    """
    unit_lower = unit.lower().strip()

    if unit_lower in WEIGHT_CONVERSIONS:
        return "weight"
    elif unit_lower in VOLUME_CONVERSIONS:
        return "volume"
    elif unit_lower in COUNT_UNITS:
        return "count"
    return None


def convert_to_base_unit(quantity: float, unit: str) -> tuple[float, str]:
    """
    Convert a quantity to its base unit (grams for weight, ml for volume).

    Args:
        quantity: The quantity to convert
        unit: The source unit code

    Returns:
        Tuple of (converted_quantity, base_unit)

    Raises:
        ValueError: If unit is not recognized
    """
    unit_lower = unit.lower().strip()

    if unit_lower in WEIGHT_CONVERSIONS:
        factor = WEIGHT_CONVERSIONS[unit_lower]
        return quantity * factor, "g"

    if unit_lower in VOLUME_CONVERSIONS:
        factor = VOLUME_CONVERSIONS[unit_lower]
        return quantity * factor, "ml"

    if unit_lower in COUNT_UNITS:
        return quantity, "count"

    raise ValueError(f"Unknown unit: {unit}")
