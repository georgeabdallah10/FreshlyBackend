#!/usr/bin/env python3
"""
Test script to verify pantry subtraction works correctly.
Creates test data and runs sync.
"""

from decimal import Decimal
from core.db import SessionLocal
from models.grocery_list import GroceryList, GroceryListItem
from models.pantry_item import PantryItem
from models.ingredient import Ingredient
from services.grocery_list_service import grocery_list_service


def main():
    db = SessionLocal()
    try:
        # Find an ingredient that exists in pantry for family 9
        # Eggs has ingredient_id=79, canonical_quantity=12, canonical_unit=pc
        egg_ingredient = db.query(Ingredient).filter(Ingredient.id == 79).first()
        if not egg_ingredient:
            print("Eggs ingredient not found")
            return
        
        print(f"Found Eggs ingredient: id={egg_ingredient.id}, name={egg_ingredient.name}")
        
        # Check pantry for eggs
        pantry_egg = db.query(PantryItem).filter(
            PantryItem.family_id == 9,
            PantryItem.ingredient_id == 79
        ).first()
        print(f"Pantry has: {pantry_egg.canonical_quantity} {pantry_egg.canonical_unit} of Eggs")
        
        # Add eggs to grocery list 8 for testing
        grocery_list = db.query(GroceryList).filter(GroceryList.id == 8).first()
        
        # Check if eggs already in list
        existing_egg = db.query(GroceryListItem).filter(
            GroceryListItem.grocery_list_id == 8,
            GroceryListItem.ingredient_id == 79
        ).first()
        
        if existing_egg:
            print(f"Eggs already in list: quantity={existing_egg.quantity}, canonical_qty={existing_egg.canonical_quantity_needed}")
        else:
            # Add 6 eggs to the grocery list
            new_item = GroceryListItem(
                grocery_list_id=8,
                ingredient_id=79,
                quantity=Decimal("20"),  # Need 20 eggs, pantry has 12 -> should have 8 remaining
                unit_id=None,
                canonical_quantity_needed=Decimal("20"),
                canonical_unit="pc",
                checked=False,
                note="20 eggs",
            )
            db.add(new_item)
            db.commit()
            print("Added 6 eggs to grocery list 8")
        
        # Now run sync
        print("\n=== Running Sync ===")
        items_removed, items_updated, remaining_items, updated_list = grocery_list_service.sync_list_with_pantry(db, grocery_list)
        
        print(f"\nSync Results:")
        print(f"  Items removed: {items_removed}")
        print(f"  Items updated: {items_updated}")
        print(f"  Remaining items: {len(remaining_items)}")
        
        # Check eggs specifically
        egg_remaining = [r for r in remaining_items if r['ingredient_id'] == 79]
        if egg_remaining:
            print(f"\n  Eggs in remaining: {egg_remaining[0]}")
        else:
            print("\n  Eggs NOT in remaining (fully covered by pantry!)")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
