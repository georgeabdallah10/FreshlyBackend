#!/usr/bin/env python3
"""
Quick script to check pantry items for a family.
"""

import sys
from core.db import SessionLocal
from models.pantry_item import PantryItem
from models.ingredient import Ingredient


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_pantry.py <family_id>")
        sys.exit(1)
    
    family_id = int(sys.argv[1])
    
    db = SessionLocal()
    try:
        items = db.query(PantryItem).filter(PantryItem.family_id == family_id).all()
        print(f"Found {len(items)} pantry items for family {family_id}:\n")
        
        for item in items:
            ingredient = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).first()
            name = ingredient.name if ingredient else f"ID:{item.ingredient_id}"
            print(f"  - {name}:")
            print(f"      quantity: {item.quantity}")
            print(f"      unit: {item.unit}")
            print(f"      canonical_quantity: {item.canonical_quantity}")
            print(f"      canonical_unit: {item.canonical_unit}")
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
