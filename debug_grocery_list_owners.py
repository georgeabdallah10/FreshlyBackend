#!/usr/bin/env python3
"""
Debug script to check grocery list owner fields in database
"""
import sys
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.grocery_list import GroceryList

def main():
    db: Session = SessionLocal()
    
    try:
        print("=== Checking Grocery Lists ===\n")
        
        # Get all grocery lists
        lists = db.query(GroceryList).limit(20).all()
        
        if not lists:
            print("No grocery lists found in database")
            return
        
        print(f"Found {len(lists)} grocery lists:\n")
        
        for gl in lists:
            print(f"List ID: {gl.id}")
            print(f"  Title: {gl.title}")
            print(f"  Family ID: {gl.family_id}")
            print(f"  Owner User ID: {gl.owner_user_id}")
            print(f"  Created By User ID: {gl.created_by_user_id}")
            print(f"  Scope: {'family' if gl.family_id else 'personal'}")
            print(f"  Status: {gl.status}")
            
            # Check constraint
            if gl.family_id and gl.owner_user_id:
                print(f"  ⚠️  WARNING: Both family_id and owner_user_id are set! (violates XOR constraint)")
            elif not gl.family_id and not gl.owner_user_id:
                print(f"  ⚠️  WARNING: Neither family_id nor owner_user_id are set!")
            else:
                print(f"  ✅ XOR constraint satisfied")
            
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
