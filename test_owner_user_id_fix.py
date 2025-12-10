#!/usr/bin/env python3
"""
Test script to verify owner_user_id is now populated with family owner for family lists
"""
import sys
from sqlalchemy.orm import Session
from core.db import SessionLocal
from crud.grocery_lists import list_grocery_lists
from schemas.grocery_list import GroceryListOut

def main():
    db: Session = SessionLocal()
    
    try:
        print("=== Testing Owner User ID Population ===\n")
        
        # Get family grocery lists
        family_lists = list_grocery_lists(db, family_id=9)
        
        if not family_lists:
            print("No family grocery lists found for family_id=9")
            print("\nTrying to get all family lists...")
            all_lists = list_grocery_lists(db)
            family_lists = [l for l in all_lists if l.family_id is not None]
            
            if not family_lists:
                print("No family lists found at all!")
                return
        
        print(f"Found {len(family_lists)} family grocery lists:\n")
        
        for gl in family_lists:
            print(f"📋 List ID: {gl.id} - '{gl.title}'")
            print(f"   Family ID: {gl.family_id}")
            print(f"   DB owner_user_id: {gl.owner_user_id} (should be NULL in DB)")
            
            # Convert to schema to see what gets returned in API
            list_out = GroceryListOut.from_orm_with_scope(gl)
            
            print(f"   API owner_user_id: {list_out.owner_user_id} (should be family owner's ID)")
            print(f"   API created_by_user_id: {list_out.created_by_user_id}")
            print(f"   API scope: {list_out.scope}")
            
            # Check family memberships
            if gl.family:
                print(f"   Family memberships:")
                for m in gl.family.memberships:
                    print(f"     - User {m.user_id}: {m.role}")
            
            if list_out.owner_user_id:
                print(f"   ✅ SUCCESS: owner_user_id populated with family owner!")
            else:
                print(f"   ❌ FAIL: owner_user_id still NULL")
            
            print()
        
        # Test personal lists too
        print("\n=== Personal Lists (for comparison) ===\n")
        personal_lists = list_grocery_lists(db, owner_user_id=13)
        
        if personal_lists:
            for gl in personal_lists[:2]:  # Just show first 2
                print(f"📋 List ID: {gl.id} - '{gl.title}'")
                list_out = GroceryListOut.from_orm_with_scope(gl)
                print(f"   DB owner_user_id: {gl.owner_user_id}")
                print(f"   API owner_user_id: {list_out.owner_user_id} (should match DB)")
                print(f"   API scope: {list_out.scope}")
                print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
