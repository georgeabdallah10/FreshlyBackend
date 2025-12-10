#!/usr/bin/env python3
"""
Test script to investigate what happens when syncing a personal grocery list
while in a family, when pantry items don't have canonical_quantity
"""
import sys
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.grocery_list import GroceryList, GroceryListItem
from models.pantry_item import PantryItem
from models.membership import FamilyMembership
from models.ingredient import Ingredient
from services.grocery_list_service import grocery_list_service
from decimal import Decimal

def main():
    db: Session = SessionLocal()
    
    try:
        print("=== Investigation: Sync Personal List w/ Family Pantry (No Canonical) ===\n")
        
        # Find a user who is in a family
        membership = db.query(FamilyMembership).filter(
            FamilyMembership.role.in_(['owner', 'admin', 'member'])
        ).first()
        
        if not membership:
            print("❌ No family memberships found!")
            return
        
        user_id = membership.user_id
        family_id = membership.family_id
        
        print(f"✅ Found user {user_id} in family {family_id}\n")
        
        # Check if user has personal grocery lists
        personal_lists = db.query(GroceryList).filter(
            GroceryList.owner_user_id == user_id
        ).all()
        
        if not personal_lists:
            print(f"No personal grocery lists found for user {user_id}")
            return
        
        print(f"Found {len(personal_lists)} personal grocery lists for user {user_id}\n")
        
        # Pick the first list
        grocery_list = personal_lists[0]
        print(f"📋 Testing with list: {grocery_list.id} - '{grocery_list.title}'")
        print(f"   Owner: {grocery_list.owner_user_id}")
        print(f"   Family: {grocery_list.family_id} (should be NULL for personal list)")
        print(f"   Items: {len(grocery_list.items)}\n")
        
        if not grocery_list.items:
            print("❌ No items in grocery list to test!")
            return
        
        # Check family pantry items
        print("=== Family Pantry Items ===")
        family_pantry = db.query(PantryItem).filter(
            PantryItem.family_id == family_id
        ).all()
        
        if not family_pantry:
            print(f"❌ No family pantry items found for family {family_id}\n")
        else:
            print(f"Found {len(family_pantry)} family pantry items:\n")
            
            for p_item in family_pantry[:5]:  # Show first 5
                ing = db.query(Ingredient).filter(Ingredient.id == p_item.ingredient_id).first()
                ing_name = ing.name if ing else f"ID:{p_item.ingredient_id}"
                
                print(f"  • {ing_name}")
                print(f"    ingredient_id: {p_item.ingredient_id}")
                print(f"    quantity: {p_item.quantity}")
                print(f"    unit: {p_item.unit}")
                print(f"    canonical_quantity: {p_item.canonical_quantity} ⚠️")
                print(f"    canonical_unit: {p_item.canonical_unit}")
                
                if p_item.canonical_quantity is None or p_item.canonical_quantity == 0:
                    print(f"    ⚠️  WARNING: No canonical quantity!")
                print()
        
        # Check personal pantry items (if any)
        print("=== Personal Pantry Items ===")
        personal_pantry = db.query(PantryItem).filter(
            PantryItem.owner_user_id == user_id
        ).all()
        
        if personal_pantry:
            print(f"Found {len(personal_pantry)} personal pantry items\n")
        else:
            print("No personal pantry items\n")
        
        # Now simulate the sync
        print("=== Simulating Sync ===")
        print("When syncing a personal list for a user in a family:")
        print("1. User is in family -> will sync against FAMILY pantry")
        print("2. If family pantry item has NO canonical_quantity:")
        print("   - get_pantry_totals_flexible() will return:")
        print("     {")
        print("       'canonical_quantity': 0 or None,")
        print("       'canonical_unit': None,")
        print("       'display_quantity': <the quantity>,")
        print("       'display_unit': <the unit>")
        print("     }")
        print("3. sync_list_with_pantry() will try to use display quantities as fallback")
        print()
        
        # Check what would happen
        from services.grocery_calculator import get_pantry_totals_flexible
        
        pantry_totals = get_pantry_totals_flexible(
            db,
            family_id=family_id,
            owner_user_id=None  # Using family pantry
        )
        
        print(f"Pantry totals found for {len(pantry_totals)} ingredients:\n")
        
        for ing_id, data in list(pantry_totals.items())[:5]:  # Show first 5
            ing = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
            ing_name = ing.name if ing else f"ID:{ing_id}"
            
            print(f"  • {ing_name} (id={ing_id})")
            print(f"    canonical: {data['canonical_quantity']} {data['canonical_unit']}")
            print(f"    display: {data['display_quantity']} {data['display_unit']}")
            
            has_canonical = data['canonical_quantity'] is not None and data['canonical_quantity'] > 0
            has_display = data['display_quantity'] is not None and data['display_quantity'] > 0
            
            if not has_canonical and has_display:
                print(f"    ⚠️  Will use DISPLAY units for comparison")
            elif has_canonical:
                print(f"    ✅ Will use CANONICAL units for comparison")
            else:
                print(f"    ❌ No quantities available!")
            print()
        
        # Check if any grocery items match pantry items
        print("=== Matching Grocery Items to Pantry ===\n")
        matches_found = 0
        
        for g_item in grocery_list.items[:5]:  # Check first 5
            ing = g_item.ingredient
            ing_name = ing.name if ing else f"ID:{g_item.ingredient_id}"
            
            print(f"📦 Grocery Item: {ing_name}")
            print(f"   quantity: {g_item.quantity}")
            print(f"   unit: {g_item.unit.code if g_item.unit else None}")
            print(f"   canonical_quantity_needed: {g_item.canonical_quantity_needed}")
            print(f"   canonical_unit: {g_item.canonical_unit}")
            
            if g_item.ingredient_id in pantry_totals:
                matches_found += 1
                pantry_data = pantry_totals[g_item.ingredient_id]
                print(f"   ✅ Found in pantry:")
                print(f"      Pantry canonical: {pantry_data['canonical_quantity']} {pantry_data['canonical_unit']}")
                print(f"      Pantry display: {pantry_data['display_quantity']} {pantry_data['display_unit']}")
                
                # Predict what will happen
                if pantry_data['canonical_quantity'] and pantry_data['canonical_unit']:
                    print(f"      → Will compare using CANONICAL units")
                elif pantry_data['display_quantity'] and pantry_data['display_unit']:
                    print(f"      → Will compare using DISPLAY units")
                    print(f"      ⚠️  May have unit mismatch issues!")
                else:
                    print(f"      → Cannot compare, will keep in list")
            else:
                print(f"   ⚪ Not in pantry")
            print()
        
        if matches_found == 0:
            print("⚠️  No grocery items match pantry items - sync would not remove anything\n")
        
        print("\n=== POTENTIAL ISSUES ===\n")
        print("1. ⚠️  If pantry has NO canonical_quantity:")
        print("   - Fallback to display quantities")
        print("   - Risk of unit mismatch (grocery=grams, pantry=cups)")
        print("   - May show warning and keep item in list")
        print()
        print("2. ⚠️  If grocery item has no canonical AND pantry has no canonical:")
        print("   - Both fall back to display units")
        print("   - Will only subtract if units exactly match")
        print()
        print("3. ✅ If either has canonical_quantity:")
        print("   - Normalization will work correctly")
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
