#!/usr/bin/env python3
"""
Debug script to test sync_list_with_pantry and verify remaining_items is populated.
"""

import sys
from decimal import Decimal
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.grocery_list import GroceryList, GroceryListItem
from models.ingredient import Ingredient
from services.grocery_list_service import grocery_list_service


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_sync_list_with_pantry(db: Session, list_id: int):
    """
    Test sync_list_with_pantry and print remaining_items.
    """
    print_header(f"Testing sync_list_with_pantry for list {list_id}")
    
    # Load grocery list with items
    grocery_list = db.query(GroceryList).filter(GroceryList.id == list_id).first()
    
    if not grocery_list:
        print(f"❌ Grocery list {list_id} not found")
        return False
    
    print(f"\nGrocery List: {grocery_list}")
    print(f"  Family ID: {grocery_list.family_id}")
    print(f"  Owner User ID: {grocery_list.owner_user_id}")
    print(f"  Number of items: {len(grocery_list.items)}")
    
    # Print item details before sync
    print("\n--- Items BEFORE sync ---")
    for item in grocery_list.items:
        ingredient = item.ingredient
        name = ingredient.name if ingredient else f"ID:{item.ingredient_id}"
        unit_code = item.unit.code if item.unit else "N/A"
        print(f"  - {name}:")
        print(f"      quantity: {item.quantity}")
        print(f"      unit: {unit_code}")
        print(f"      canonical_quantity_needed: {item.canonical_quantity_needed}")
        print(f"      canonical_unit: {item.canonical_unit}")
        print(f"      checked: {item.checked}")
        print(f"      note: {item.note}")
    
    # Call sync_list_with_pantry
    try:
        items_removed, items_updated, remaining_items, updated_list = grocery_list_service.sync_list_with_pantry(
            db, grocery_list
        )
        
        print(f"\n--- Sync Results ---")
        print(f"  Items removed: {items_removed}")
        print(f"  Items updated: {items_updated}")
        print(f"  Remaining items count: {len(remaining_items)}")
        
        print("\n--- Remaining Items ---")
        if remaining_items:
            for item in remaining_items:
                print(f"  - {item['ingredient_name']}:")
                print(f"      ingredient_id: {item['ingredient_id']}")
                print(f"      quantity: {item['quantity']}")
                print(f"      unit_code: {item['unit_code']}")
                print(f"      canonical_quantity: {item.get('canonical_quantity')}")
                print(f"      canonical_unit: {item.get('canonical_unit')}")
                print(f"      note: {item.get('note')}")
        else:
            print("  (empty list)")
        
        return True
        
    except Exception as e:
        print(f"❌ Exception during sync: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_sync_pantry_debug.py <list_id>")
        print("\nThis script tests sync_list_with_pantry and shows remaining_items.")
        sys.exit(1)
    
    list_id = int(sys.argv[1])
    
    db = SessionLocal()
    try:
        test_sync_list_with_pantry(db, list_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
