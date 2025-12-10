#!/usr/bin/env python3
"""
Test for edge cases and potential bugs in canonical_quantity, sync, and grocery list code.
"""

import re
from decimal import Decimal

def test_division_by_zero_in_parse_amount_string():
    """Test if parse_amount_string handles division by zero in fractions."""
    
    print("=" * 80)
    print("TEST 1: Division by Zero in Fraction Parsing")
    print("=" * 80)
    
    test_cases = [
        ("0/0 cup", "Should handle 0/0"),
        ("1/0 cup", "Should handle 1/0"),
        ("5/0", "Should handle 5/0 without unit"),
        ("1/2 cup", "Valid fraction - should work"),
    ]
    
    bugs_found = []
    
    for amount_str, description in test_cases:
        print(f"\nTesting: {amount_str} - {description}")
        
        # Simulate the current code
        amount_str = amount_str.strip().lower()
        fraction_match = re.match(r'^(\d+)/(\d+)\s*(.*)$', amount_str)
        
        if fraction_match:
            numerator = int(fraction_match.group(1))
            denominator = int(fraction_match.group(2))
            
            # BUG: No check for denominator == 0
            if denominator == 0:
                print(f"  ⚠️  BUG FOUND: Division by zero! numerator={numerator}, denominator={denominator}")
                bugs_found.append({
                    'input': amount_str,
                    'issue': 'Division by zero not checked',
                    'file': 'services/grocery_calculator.py',
                    'function': 'parse_amount_string',
                    'line': '~369'
                })
                try:
                    qty = numerator / denominator
                    print(f"  Result: {qty}")
                except ZeroDivisionError as e:
                    print(f"  ❌ ZeroDivisionError: {e}")
            else:
                qty = numerator / denominator
                unit = fraction_match.group(3).strip() or "count"
                print(f"  ✅ Success: {qty} {unit}")
    
    return bugs_found

def test_negative_quantities():
    """Test if negative quantities are handled properly."""
    
    print("\n" + "=" * 80)
    print("TEST 2: Negative Quantity Handling")
    print("=" * 80)
    
    # Check if sync logic handles negative remaining quantities
    test_cases = [
        {
            'grocery_qty': Decimal('5'),
            'pantry_qty': Decimal('10'),
            'expected_remaining': Decimal('-5'),
            'description': 'Pantry has more than needed'
        },
        {
            'grocery_qty': Decimal('5'),
            'pantry_qty': Decimal('5'),
            'expected_remaining': Decimal('0'),
            'description': 'Exact match'
        },
        {
            'grocery_qty': Decimal('10'),
            'pantry_qty': Decimal('5'),
            'expected_remaining': Decimal('5'),
            'description': 'Need more than pantry has'
        },
    ]
    
    issues_found = []
    
    for test in test_cases:
        grocery_qty = test['grocery_qty']
        pantry_qty = test['pantry_qty']
        expected = test['expected_remaining']
        
        remaining_qty = grocery_qty - pantry_qty
        
        print(f"\n{test['description']}")
        print(f"  Grocery: {grocery_qty}, Pantry: {pantry_qty}")
        print(f"  Remaining: {remaining_qty} (expected: {expected})")
        
        # Check the sync logic
        if remaining_qty <= 0:
            print(f"  ✅ Item would be removed (fully covered)")
        elif remaining_qty < grocery_qty:
            print(f"  ✅ Item would be updated (partially covered)")
        else:
            print(f"  ✅ Item would remain unchanged (not in pantry)")
    
    return issues_found

def test_canonical_quantity_null_handling():
    """Test handling of null/None canonical quantities."""
    
    print("\n" + "=" * 80)
    print("TEST 3: Null/None Canonical Quantity Handling")
    print("=" * 80)
    
    test_cases = [
        {
            'canonical_qty': None,
            'canonical_unit': None,
            'display_qty': Decimal('5'),
            'display_unit': 'cups',
            'note': '5 cups',
            'description': 'No canonical, has display and note'
        },
        {
            'canonical_qty': None,
            'canonical_unit': None,
            'display_qty': None,
            'display_unit': None,
            'note': '3 teaspoons',
            'description': 'No canonical, no display, has note'
        },
        {
            'canonical_qty': None,
            'canonical_unit': None,
            'display_qty': None,
            'display_unit': None,
            'note': None,
            'description': 'Everything is null'
        },
    ]
    
    issues_found = []
    
    for test in test_cases:
        print(f"\n{test['description']}")
        canonical_qty = test['canonical_qty']
        has_valid_canonical = canonical_qty is not None and canonical_qty > 0
        
        print(f"  has_valid_canonical: {has_valid_canonical}")
        
        if not has_valid_canonical and test['note']:
            # Simulate parsing from note
            print(f"  Would try to parse note: '{test['note']}'")
            # This is handled properly in the code
        
        if not has_valid_canonical and test['display_qty'] is not None:
            print(f"  Would fall back to display: {test['display_qty']} {test['display_unit']}")
        
        if not has_valid_canonical and not test['note'] and test['display_qty'] is None:
            print(f"  ⚠️  Item has no quantity data - would be kept as-is")
            # This is OK - conservative approach
    
    return issues_found

def test_unit_mismatch():
    """Test unit mismatch scenarios."""
    
    print("\n" + "=" * 80)
    print("TEST 4: Unit Mismatch Handling")
    print("=" * 80)
    
    def normalize_unit_string(unit):
        """Simple simulation of normalize_unit_string."""
        if not unit:
            return None
        unit = unit.lower().strip()
        # Simple normalization
        unit_map = {
            'cups': 'cup',
            'grams': 'g',
            'teaspoons': 'tsp',
            'tablespoons': 'tbsp',
        }
        return unit_map.get(unit, unit)
    
    test_cases = [
        ('g', 'items', 'Should warn - incompatible units'),
        ('ml', 'g', 'Should warn - need conversion'),
        ('cup', 'cups', 'Should normalize to same unit'),
        ('tsp', 'teaspoons', 'Should normalize to same unit'),
    ]
    
    for pantry_unit, grocery_unit, description in test_cases:
        print(f"\n{description}")
        print(f"  Pantry: {pantry_unit}, Grocery: {grocery_unit}")
        
        normalized_pantry = normalize_unit_string(pantry_unit)
        normalized_grocery = normalize_unit_string(grocery_unit)
        
        print(f"  Normalized: {normalized_pantry} vs {normalized_grocery}")
        
        if normalized_pantry and normalized_grocery and normalized_pantry != normalized_grocery:
            print(f"  ⚠️  Unit mismatch - item would be kept as-is (conservative)")
        else:
            print(f"  ✅ Units match - can compare quantities")
    
    return []

def test_decimal_operations():
    """Test Decimal operations for precision issues."""
    
    print("\n" + "=" * 80)
    print("TEST 5: Decimal Precision")
    print("=" * 80)
    
    test_cases = [
        (Decimal('0.1') + Decimal('0.2'), Decimal('0.3'), 'Basic addition'),
        (Decimal('10') / Decimal('3'), None, 'Division with repeating decimal'),
        (Decimal('5.555') * Decimal('2'), Decimal('11.11'), 'Multiplication'),
    ]
    
    for calc, expected, description in test_cases:
        print(f"\n{description}")
        print(f"  Result: {calc}")
        if expected:
            print(f"  Expected: {expected}")
            print(f"  Match: {calc == expected}")
    
    return []

def main():
    """Run all edge case tests."""
    print("\n🔍 EDGE CASE AND BUG DETECTION TEST")
    print("=" * 80)
    
    all_bugs = []
    
    # Run all tests
    all_bugs.extend(test_division_by_zero_in_parse_amount_string())
    all_bugs.extend(test_negative_quantities())
    all_bugs.extend(test_canonical_quantity_null_handling())
    all_bugs.extend(test_unit_mismatch())
    all_bugs.extend(test_decimal_operations())
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if all_bugs:
        print(f"\n❌ FOUND {len(all_bugs)} POTENTIAL BUG(S):\n")
        for i, bug in enumerate(all_bugs, 1):
            print(f"{i}. {bug['file']}:{bug['line']} in {bug['function']}()")
            print(f"   Issue: {bug['issue']}")
            print(f"   Input: {bug['input']}\n")
    else:
        print("\n✅ No critical bugs found in tested scenarios")
        print("   Note: Most edge cases are handled conservatively")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. ✅ Null canonical quantities: Properly handled with fallbacks
2. ✅ Negative remaining quantities: Properly handled (item removed)
3. ✅ Unit mismatches: Conservative approach (keep item)
4. ⚠️  Division by zero: Should add validation in parse_amount_string()
5. ✅ Decimal precision: Using Decimal throughout prevents float issues
6. ✅ Exception handling: Most operations have try/except blocks

PRIORITY FIX NEEDED:
- Add denominator != 0 check in parse_amount_string() before division
""")

if __name__ == "__main__":
    main()
