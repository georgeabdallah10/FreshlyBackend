#!/usr/bin/env python3
"""
Quick script to check ingredients in pantry and grocery list.
"""

import sys
from core.db import SessionLocal
from models.pantry_item import PantryItem
from models.grocery_list import GroceryList, GroceryListItem
from models.ingredient import Ingredient


def main():
    db = SessionLocal()
    try:
        # Get pantry ingredients for family 9
        print("=== Pantry Items (Family 9) ===")
        pantry_items = db.query(PantryItem).filter(PantryItem.family_id == 9).all()
        for item in pantry_items:
            print(f"  ingredient_id={item.ingredient_id}, name='{item.ingredient.name if item.ingredient else 'N/A'}'")
        
        print("\n=== Grocery List 8 Items ===")
        grocery_list = db.query(GroceryList).filter(GroceryList.id == 8).first()
        for item in grocery_list.items:
            print(f"  ingredient_id={item.ingredient_id}, name='{item.ingredient.name if item.ingredient else 'N/A'}'")
        
        print("\n=== Grocery List 10 Items ===")
        grocery_list = db.query(GroceryList).filter(GroceryList.id == 10).first()
        for item in grocery_list.items:
            print(f"  ingredient_id={item.ingredient_id}, name='{item.ingredient.name if item.ingredient else 'N/A'}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
