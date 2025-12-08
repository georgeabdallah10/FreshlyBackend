#!/usr/bin/env python3
"""
Test script for Phase 3 grocery list sync functionality.

Tests:
1. calculate_total_needed - Multiple ingredients with servings multipliers
2. compute_remaining_to_buy - Pantry subtraction
3. mark_item_purchased - Idempotency check
4. Manual items preserved during rebuild
"""

import sys
from decimal import Decimal
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.user import User
from models.family import Family
from models.membership import FamilyMembership
from models.meal_plan import MealPlan, MealSlot, MealSlotMeal
from models.meal import Meal
from models.ingredient import Ingredient
from models.pantry_item import PantryItem
from models.grocery_list import GroceryList, GroceryListItem
from services.grocery_calculator import (
    calculate_total_needed,
    get_pantry_totals,
    compute_remaining_to_buy,
    format_for_display,
)
from services.grocery_list_service import grocery_list_service


def print_header(title: str):
    """Print formatted test section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(success: bool, message: str):
    """Print test result with emoji"""
    emoji = "✅" if success else "❌"
    print(f"{emoji} {message}")


def test_calculate_total_needed(db: Session, meal_plan_id: int) -> bool:
    """
    Test calculate_total_needed with multiple ingredients and servings multipliers.
    """
    print_header("TEST: calculate_total_needed")
    
    try:
        totals = calculate_total_needed(db, meal_plan_id)
        
        if not totals:
            print_result(False, f"No ingredients found for meal plan {meal_plan_id}")
            return False
        
        print(f"\nFound {len(totals)} unique ingredients:")
        for ing_id, (qty, unit) in totals.items():
            ingredient = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
            name = ingredient.name if ingredient else f"ID:{ing_id}"
            print(f"  - {name}: {qty} {unit}")
        
        # Verify quantities are positive
        all_positive = all(qty > 0 for qty, _ in totals.values())
        print_result(all_positive, "All quantities are positive")
        
        # Verify canonical units are set
        all_have_units = all(unit is not None for _, unit in totals.values())
        print_result(all_have_units, "All ingredients have canonical units")
        
        return all_positive and all_have_units
        
    except Exception as e:
        print_result(False, f"Exception: {e}")
        return False


def test_compute_remaining_to_buy(db: Session, meal_plan_id: int) -> bool:
    """
    Test compute_remaining_to_buy correctly subtracts pantry from needed.
    """
    print_header("TEST: compute_remaining_to_buy")
    
    try:
        # Get meal plan scope
        meal_plan = db.query(MealPlan).filter(MealPlan.id == meal_plan_id).first()
        if not meal_plan:
            print_result(False, f"Meal plan {meal_plan_id} not found")
            return False
        
        # Calculate total needed
        total_needed = calculate_total_needed(db, meal_plan_id)
        print(f"\nTotal needed: {len(total_needed)} ingredients")
        
        # Get pantry totals
        pantry_totals = get_pantry_totals(
            db,
            family_id=meal_plan.family_id,
            owner_user_id=meal_plan.owner_user_id,
        )
        print(f"In pantry: {len(pantry_totals)} ingredients")
        
        # Compute remaining
        remaining = compute_remaining_to_buy(total_needed, pantry_totals)
        print(f"Remaining to buy: {len(remaining)} ingredients")
        
        # Verify math: remaining = needed - pantry (but >= 0)
        for ing_id, (remain_qty, remain_unit) in remaining.items():
            needed_qty, _ = total_needed.get(ing_id, (Decimal(0), None))
            pantry_qty, _ = pantry_totals.get(ing_id, (Decimal(0), None))
            expected = max(Decimal(0), needed_qty - pantry_qty)
            
            if remain_qty != expected:
                print_result(False, f"Ingredient {ing_id}: expected {expected}, got {remain_qty}")
                return False
        
        # Items fully covered by pantry should NOT be in remaining
        fully_covered = set(total_needed.keys()) - set(remaining.keys())
        for ing_id in fully_covered:
            needed_qty, _ = total_needed.get(ing_id, (Decimal(0), None))
            pantry_qty, _ = pantry_totals.get(ing_id, (Decimal(0), None))
            if pantry_qty < needed_qty:
                print_result(False, f"Ingredient {ing_id} missing from remaining but not fully covered")
                return False
        
        print_result(True, "Remaining calculation is correct")
        print_result(True, f"{len(fully_covered)} ingredients fully covered by pantry")
        
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {e}")
        return False


def test_mark_item_purchased_idempotency(db: Session, grocery_list_item_id: int, user_id: int) -> bool:
    """
    Test mark_item_purchased is idempotent - calling it twice doesn't double-add to pantry.
    """
    print_header("TEST: mark_item_purchased idempotency")
    
    try:
        # Get the item first
        item = db.query(GroceryListItem).filter(GroceryListItem.id == grocery_list_item_id).first()
        if not item:
            print_result(False, f"GroceryListItem {grocery_list_item_id} not found")
            return False
        
        print(f"\nItem: {item.ingredient.name if item.ingredient else 'Unknown'}")
        print(f"Canonical quantity: {item.canonical_quantity_needed} {item.canonical_unit}")
        
        # First call
        item1, pantry1 = grocery_list_service.mark_item_purchased(
            db, grocery_list_item_id, user_id
        )
        first_pantry_qty = pantry1.canonical_quantity
        print(f"\nFirst call:")
        print(f"  is_purchased: {item1.is_purchased}")
        print(f"  Pantry quantity: {first_pantry_qty}")
        
        # Second call (should be idempotent)
        item2, pantry2 = grocery_list_service.mark_item_purchased(
            db, grocery_list_item_id, user_id
        )
        second_pantry_qty = pantry2.canonical_quantity
        print(f"\nSecond call:")
        print(f"  is_purchased: {item2.is_purchased}")
        print(f"  Pantry quantity: {second_pantry_qty}")
        
        # Verify idempotency
        quantities_equal = first_pantry_qty == second_pantry_qty
        is_still_purchased = item2.is_purchased
        
        print_result(quantities_equal, "Pantry quantity unchanged after second call")
        print_result(is_still_purchased, "Item still marked as purchased")
        
        return quantities_equal and is_still_purchased
        
    except Exception as e:
        print_result(False, f"Exception: {e}")
        return False


def test_manual_items_preserved(db: Session, meal_plan_id: int, user_id: int) -> bool:
    """
    Test that manual items (is_manual=True) are preserved during rebuild.
    """
    print_header("TEST: Manual items preserved during rebuild")
    
    try:
        # Get or create grocery list for meal plan
        grocery_list = db.query(GroceryList).filter(
            GroceryList.meal_plan_id == meal_plan_id
        ).first()
        
        if not grocery_list:
            print_result(False, f"No grocery list found for meal plan {meal_plan_id}")
            print("  Run rebuild first, then add a manual item to test")
            return False
        
        # Find or create a test ingredient
        test_ingredient = db.query(Ingredient).filter(
            Ingredient.name.ilike("%test%")
        ).first()
        
        if not test_ingredient:
            test_ingredient = Ingredient(
                name="test_manual_item",
                canonical_unit="count",
                category="test",
            )
            db.add(test_ingredient)
            db.flush()
        
        # Add a manual item to the list
        manual_item = GroceryListItem(
            grocery_list_id=grocery_list.id,
            ingredient_id=test_ingredient.id,
            quantity=Decimal("5"),
            unit_id=None,
            canonical_quantity_needed=Decimal("5"),
            canonical_unit="count",
            checked=False,
            is_purchased=False,
            is_manual=True,
            source_meal_plan_id=None,  # Manual items don't have a source meal plan
        )
        db.add(manual_item)
        db.commit()
        
        manual_item_id = manual_item.id
        print(f"\nAdded manual item ID: {manual_item_id}")
        
        # Count items before rebuild
        items_before = len(grocery_list.items)
        print(f"Items before rebuild: {items_before}")
        
        # Rebuild the grocery list
        updated_list = grocery_list_service.rebuild_grocery_list_from_meal_plan(
            db, meal_plan_id, user_id
        )
        
        # Refresh and check
        db.refresh(updated_list)
        items_after = len(updated_list.items)
        print(f"Items after rebuild: {items_after}")
        
        # Check if manual item still exists
        manual_item_exists = any(
            item.id == manual_item_id for item in updated_list.items
        )
        
        print_result(manual_item_exists, "Manual item preserved after rebuild")
        
        # Cleanup: remove test manual item
        db.query(GroceryListItem).filter(GroceryListItem.id == manual_item_id).delete()
        db.commit()
        
        return manual_item_exists
        
    except Exception as e:
        print_result(False, f"Exception: {e}")
        db.rollback()
        return False


def test_purchased_items_preserved(db: Session, meal_plan_id: int, user_id: int) -> bool:
    """
    Test that purchased items (is_purchased=True) are preserved during rebuild.
    """
    print_header("TEST: Purchased items preserved during rebuild")
    
    try:
        # Rebuild to ensure we have a grocery list
        grocery_list = grocery_list_service.rebuild_grocery_list_from_meal_plan(
            db, meal_plan_id, user_id
        )
        db.refresh(grocery_list)
        
        if not grocery_list.items:
            print_result(False, "No items in grocery list to test")
            return False
        
        # Pick first unpurchased item
        test_item = None
        for item in grocery_list.items:
            if not item.is_purchased and item.source_meal_plan_id == meal_plan_id:
                test_item = item
                break
        
        if not test_item:
            print_result(False, "No unpurchased auto-generated items found to test")
            return False
        
        test_item_id = test_item.id
        test_ingredient_id = test_item.ingredient_id
        print(f"\nMarking item {test_item_id} as purchased")
        
        # Mark it as purchased
        grocery_list_service.mark_item_purchased(db, test_item_id, user_id)
        
        # Verify it's purchased
        db.refresh(test_item)
        print(f"Item is_purchased: {test_item.is_purchased}")
        
        # Rebuild the grocery list
        print("Rebuilding grocery list...")
        updated_list = grocery_list_service.rebuild_grocery_list_from_meal_plan(
            db, meal_plan_id, user_id
        )
        db.refresh(updated_list)
        
        # Check if purchased item still exists
        purchased_item_exists = any(
            item.id == test_item_id and item.is_purchased 
            for item in updated_list.items
        )
        
        print_result(purchased_item_exists, "Purchased item preserved after rebuild")
        
        return purchased_item_exists
        
    except Exception as e:
        print_result(False, f"Exception: {e}")
        db.rollback()
        return False


def test_debug_meal_plan_requirements(db: Session, meal_plan_id: int, user_id: int) -> bool:
    """
    Test the debug helper returns proper data structure.
    """
    print_header("TEST: debug_meal_plan_requirements")
    
    try:
        debug_info = grocery_list_service.debug_meal_plan_requirements(
            db, meal_plan_id, user_id
        )
        
        # Verify required keys exist
        required_keys = ["meal_plan_id", "summary", "ingredients"]
        for key in required_keys:
            if key not in debug_info:
                print_result(False, f"Missing key: {key}")
                return False
        
        print(f"\nMeal plan: {debug_info.get('meal_plan_title')}")
        print(f"Scope: {debug_info.get('scope')}")
        
        summary = debug_info["summary"]
        print(f"\nSummary:")
        print(f"  Total ingredients needed: {summary.get('total_ingredients_needed')}")
        print(f"  Ingredients in pantry: {summary.get('ingredients_in_pantry')}")
        print(f"  Ingredients to buy: {summary.get('ingredients_to_buy')}")
        print(f"  Fully covered: {summary.get('fully_covered_count')}")
        
        # Verify ingredient details structure
        ingredients = debug_info["ingredients"]
        if ingredients:
            sample = ingredients[0]
            required_ing_keys = ["ingredient_id", "ingredient_name", "needed", 
                                "available_in_pantry", "remaining_to_buy"]
            for key in required_ing_keys:
                if key not in sample:
                    print_result(False, f"Missing ingredient key: {key}")
                    return False
        
        print_result(True, "Debug info structure is correct")
        print(f"\nFirst 5 ingredients:")
        for ing in ingredients[:5]:
            print(f"  {ing['ingredient_name']}: need {ing['needed']}, "
                  f"have {ing['available_in_pantry']}, buy {ing['remaining_to_buy']}")
        
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {e}")
        return False


def run_all_tests():
    """Run all grocery sync tests"""
    db: Session = SessionLocal()
    
    print("\n" + "="*60)
    print("  GROCERY SYNC SYSTEM TESTS")
    print("="*60)
    
    try:
        # Find a test user
        user = db.query(User).first()
        if not user:
            print_result(False, "No users found in database")
            return False
        print(f"\nUsing user: {user.name} (ID: {user.id})")
        
        # Find a meal plan with grocery list
        meal_plan = db.query(MealPlan).join(
            GroceryList, GroceryList.meal_plan_id == MealPlan.id
        ).first()
        
        if not meal_plan:
            # Try any meal plan
            meal_plan = db.query(MealPlan).first()
        
        if not meal_plan:
            print_result(False, "No meal plans found in database")
            print("  Please create a meal plan first")
            return False
        
        print(f"Using meal plan: {meal_plan.title or meal_plan.id}")
        
        # Run tests
        results = []
        
        # Test 1: calculate_total_needed
        results.append(test_calculate_total_needed(db, meal_plan.id))
        
        # Test 2: compute_remaining_to_buy  
        results.append(test_compute_remaining_to_buy(db, meal_plan.id))
        
        # Test 3: debug_meal_plan_requirements
        results.append(test_debug_meal_plan_requirements(db, meal_plan.id, user.id))
        
        # Test 4: Manual items preserved
        results.append(test_manual_items_preserved(db, meal_plan.id, user.id))
        
        # Test 5: Purchased items preserved
        results.append(test_purchased_items_preserved(db, meal_plan.id, user.id))
        
        # Find a grocery list item for idempotency test
        grocery_list = db.query(GroceryList).filter(
            GroceryList.meal_plan_id == meal_plan.id
        ).first()
        
        if grocery_list and grocery_list.items:
            # Create a fresh item for testing
            test_item = None
            for item in grocery_list.items:
                if not item.is_purchased:
                    test_item = item
                    break
            
            if test_item:
                results.append(test_mark_item_purchased_idempotency(db, test_item.id, user.id))
            else:
                print_header("TEST: mark_item_purchased idempotency")
                print_result(False, "No unpurchased items to test idempotency")
        else:
            print_header("TEST: mark_item_purchased idempotency")
            print_result(False, "No grocery list found for idempotency test")
        
        # Summary
        print("\n" + "="*60)
        print("  TEST SUMMARY")
        print("="*60)
        passed = sum(results)
        total = len(results)
        print(f"\n{passed}/{total} tests passed")
        
        return passed == total
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
