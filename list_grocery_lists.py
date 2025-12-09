#!/usr/bin/env python3
"""
Quick script to list grocery lists in the database.
"""

from core.db import SessionLocal
from models.grocery_list import GroceryList


def main():
    db = SessionLocal()
    try:
        lists = db.query(GroceryList).limit(10).all()
        print(f"Found {len(lists)} grocery lists (showing up to 10):\n")
        
        for g in lists:
            print(f"  ID: {g.id}")
            print(f"    Family ID: {g.family_id}")
            print(f"    Owner User ID: {g.owner_user_id}")
            print(f"    Title: {g.title}")
            print(f"    Items count: {len(g.items)}")
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
