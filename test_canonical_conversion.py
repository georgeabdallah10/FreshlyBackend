#!/usr/bin/env python3
"""
Test: Mustard 5ml (pantry) vs 3 teaspoons (grocery)
Demonstrates canonical unit conversion and sync
"""
from decimal import Decimal
from core.unit_conversions import convert_to_base_unit

print("=" * 60)
print("CANONICAL UNIT CONVERSION TEST")
print("=" * 60)
print()

# Example 1: Your Mustard Example
print("🧪 Example 1: Mustard")
print("-" * 60)

# Grocery item: 3 teaspoons
grocery_qty = 3.0
grocery_unit = "tsp"

# Convert to canonical
canonical_qty, canonical_unit = convert_to_base_unit(grocery_qty, grocery_unit)
print(f"Grocery Item: {grocery_qty} {grocery_unit}")
print(f"  → Canonical: {canonical_qty} {canonical_unit}")
print()

# Pantry item: 5 ml
pantry_qty = 5.0
pantry_unit = "ml"
pantry_canonical_qty, pantry_canonical_unit = convert_to_base_unit(pantry_qty, pantry_unit)
print(f"Pantry Item: {pantry_qty} {pantry_unit}")
print(f"  → Canonical: {pantry_canonical_qty} {pantry_canonical_unit}")
print()

# Sync calculation
print("Sync Calculation:")
print(f"  Needed: {canonical_qty} {canonical_unit}")
print(f"  Have:   {pantry_canonical_qty} {pantry_canonical_unit}")

if canonical_unit == pantry_canonical_unit:
    remaining = canonical_qty - pantry_canonical_qty
    print(f"  Units match! ✅")
    print(f"  Remaining: {remaining} {canonical_unit}")
    
    if remaining <= 0:
        print(f"  → Item REMOVED (fully covered)")
    elif remaining < canonical_qty:
        print(f"  → Item UPDATED to {remaining} {canonical_unit}")
        # Convert back to tsp
        tsp_remaining = remaining / 5.0
        print(f"     (equivalent to {tsp_remaining} tsp)")
    else:
        print(f"  → Item KEPT (not in pantry)")
else:
    print(f"  Units don't match! ⚠️")
    print(f"  → Item KEPT as-is (unit mismatch)")

print()
print()

# Example 2: Oil - 2 cups vs 500ml
print("🧪 Example 2: Oil - 2 cups (grocery) vs 500ml (pantry)")
print("-" * 60)

grocery_qty = 2.0
grocery_unit = "cup"
canonical_qty, canonical_unit = convert_to_base_unit(grocery_qty, grocery_unit)
print(f"Grocery: {grocery_qty} {grocery_unit} → {canonical_qty} {canonical_unit}")

pantry_qty = 500.0
pantry_unit = "ml"
pantry_canonical_qty, pantry_canonical_unit = convert_to_base_unit(pantry_qty, pantry_unit)
print(f"Pantry: {pantry_qty} {pantry_unit} → {pantry_canonical_qty} {pantry_canonical_unit}")

remaining = canonical_qty - pantry_canonical_qty
print(f"Remaining: {canonical_qty} - {pantry_canonical_qty} = {remaining} {canonical_unit}")

if remaining <= 0:
    print(f"✅ REMOVED (fully covered)")
else:
    print(f"✅ UPDATED to {remaining} {canonical_unit}")

print()
print()

# Example 3: Chicken - 1 lb vs 500g
print("🧪 Example 3: Chicken - 1 lb (grocery) vs 500g (pantry)")
print("-" * 60)

grocery_qty = 1.0
grocery_unit = "lb"
canonical_qty, canonical_unit = convert_to_base_unit(grocery_qty, grocery_unit)
print(f"Grocery: {grocery_qty} {grocery_unit} → {canonical_qty} {canonical_unit}")

pantry_qty = 500.0
pantry_unit = "g"
pantry_canonical_qty, pantry_canonical_unit = convert_to_base_unit(pantry_qty, pantry_unit)
print(f"Pantry: {pantry_qty} {pantry_unit} → {pantry_canonical_qty} {pantry_canonical_unit}")

remaining = canonical_qty - pantry_canonical_qty
print(f"Remaining: {canonical_qty} - {pantry_canonical_qty} = {remaining} {canonical_unit}")

if remaining <= 0:
    print(f"✅ REMOVED (fully covered)")
else:
    print(f"✅ UPDATED to {remaining} {canonical_unit}")
    print(f"   (equivalent to {remaining / 453.592:.2f} lb)")

print()
print()

# Example 4: Mixed units that DON'T match
print("🧪 Example 4: Unit Mismatch - 2 cups (grocery) vs 200g (pantry)")
print("-" * 60)

grocery_qty = 2.0
grocery_unit = "cup"
canonical_qty, canonical_unit = convert_to_base_unit(grocery_qty, grocery_unit)
print(f"Grocery: {grocery_qty} {grocery_unit} → {canonical_qty} {canonical_unit} (volume)")

pantry_qty = 200.0
pantry_unit = "g"
pantry_canonical_qty, pantry_canonical_unit = convert_to_base_unit(pantry_qty, pantry_unit)
print(f"Pantry: {pantry_qty} {pantry_unit} → {pantry_canonical_qty} {pantry_canonical_unit} (weight)")

if canonical_unit != pantry_canonical_unit:
    print(f"⚠️  UNIT MISMATCH: {canonical_unit} != {pantry_canonical_unit}")
    print(f"   Cannot compare volume and weight directly!")
    print(f"   → Item KEPT in list, user must verify manually")
else:
    remaining = canonical_qty - pantry_canonical_qty
    print(f"Remaining: {remaining} {canonical_unit}")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print()
print("✅ Same unit type → Perfect sync!")
print("   - tsp, tbsp, cup, ml, l → all convert to 'ml'")
print("   - oz, lb, kg, g → all convert to 'g'")
print("   - count, pieces, units → all convert to 'count'")
print()
print("⚠️  Different unit types → Unit mismatch warning")
print("   - volume vs weight → Cannot compare")
print("   - Item stays in list for manual verification")
print()
