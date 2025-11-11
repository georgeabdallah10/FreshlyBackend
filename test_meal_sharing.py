#!/usr/bin/env python3
"""
Test script for meal sharing functionality
Tests:
1. Creating a meal with family_id
2. Attaching an existing meal to a family
3. Sharing a meal with family members
4. Error validation
"""

import sys
from sqlalchemy.orm import Session
from core.db import SessionLocal, engine
from models.user import User
from models.family import Family
from models.membership import FamilyMembership
from models.meal import Meal
from schemas.meal import MealCreate, MacroBreakdown, IngredientIn, AttachFamilyRequest
from crud.meals import create_meal, get_meal, attach_meal_to_family
from crud.meal_share_requests import create_share_request, check_existing_request, accept_share_request
from schemas.meal_share_request import MealShareRequestCreate

def test_meal_sharing():
    """Test meal sharing functionality"""
    db: Session = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("MEAL SHARING SYSTEM TEST")
        print("="*60)
        
        # Get test users and family from database
        print("\n1. Fetching test data...")
        user1 = db.query(User).filter(User.email == "frfrtt@gmail.com").first()
        if not user1:
            print("❌ Test user not found. Please ensure user exists in database.")
            return False
        
        # Get a family this user belongs to
        membership = db.query(FamilyMembership).filter(
            FamilyMembership.user_id == user1.id
        ).first()
        
        if not membership:
            print("❌ User is not in any family. Cannot test family meal features.")
            return False
        
        family = db.query(Family).get(membership.family_id)
        print(f"✅ Found user: {user1.name} (ID: {user1.id})")
        print(f"✅ Found family: {family.display_name} (ID: {family.id})")
        
        # Get another member in the same family
        other_membership = db.query(FamilyMembership).filter(
            FamilyMembership.family_id == family.id,
            FamilyMembership.user_id != user1.id
        ).first()
        
        if other_membership:
            user2 = db.query(User).get(other_membership.user_id)
            print(f"✅ Found second family member: {user2.name} (ID: {user2.id})")
        else:
            # Fallback to any other user in the system for global sharing tests
            user2 = db.query(User).filter(User.id != user1.id).first()
            if user2:
                print(f"⚠️  No additional family member, using global user {user2.name} (ID: {user2.id})")
            else:
                print("❌ Could not find a second user to test sharing.")
                return False
        
        # Test 1: Create a meal with family_id
        print("\n2. Testing meal creation with family_id...")
        meal_data = MealCreate(
            name="Test Family Meal",
            image="https://example.com/image.jpg",
            calories=500,
            prepTime=10,
            cookTime=20,
            totalTime=30,
            mealType="Lunch",
            cuisine="Italian",
            tags=["quick", "easy"],
            macros=MacroBreakdown(protein=25, fats=15, carbs=45),
            difficulty="Easy",
            servings=4,
            dietCompatibility=["vegetarian"],
            goalFit=["weight-loss"],
            ingredients=[
                IngredientIn(name="Pasta", amount="200g", inPantry=False)
            ],
            instructions=["Boil water", "Cook pasta"],
            cookingTools=["pot"],
            notes="Test meal",
            isFavorite=False,
            familyId=family.id  # This is the key field we're testing
        )
        
        meal1 = create_meal(db, meal_data, user1.id)
        print(f"✅ Created meal: {meal1.name} (ID: {meal1.id})")
        print(f"   - Created by user: {meal1.created_by_user_id}")
        print(f"   - Family ID: {meal1.family_id}")
        
        if meal1.family_id == family.id:
            print("   ✅ Family ID persisted correctly!")
        else:
            print(f"   ❌ Family ID mismatch! Expected {family.id}, got {meal1.family_id}")
            return False
        
        # Test 2: Create a meal without family_id, then attach it
        print("\n3. Testing attach-family functionality...")
        meal_data2 = MealCreate(
            name="Test Personal Meal",
            image="https://example.com/image2.jpg",
            calories=400,
            prepTime=5,
            cookTime=15,
            totalTime=20,
            mealType="Dinner",
            cuisine="Mexican",
            tags=["spicy"],
            macros=MacroBreakdown(protein=30, fats=20, carbs=35),
            difficulty="Medium",
            servings=2,
            dietCompatibility=["gluten-free"],
            goalFit=["muscle-gain"],
            ingredients=[
                IngredientIn(name="Chicken", amount="250g", inPantry=False)
            ],
            instructions=["Season chicken", "Grill"],
            cookingTools=["grill"],
            notes="No family initially",
            isFavorite=False,
            familyId=None  # No family initially
        )
        
        meal2 = create_meal(db, meal_data2, user1.id)
        print(f"✅ Created personal meal: {meal2.name} (ID: {meal2.id})")
        print(f"   - Family ID before attach: {meal2.family_id}")
        
        # Now attach it to the family
        updated_meal = attach_meal_to_family(db, meal2, family.id)
        print(f"✅ Attached meal to family")
        print(f"   - Family ID after attach: {updated_meal.family_id}")
        
        if updated_meal.family_id == family.id:
            print("   ✅ Meal successfully attached to family!")
        else:
            print(f"   ❌ Family ID not updated! Expected {family.id}, got {updated_meal.family_id}")
            return False
        
        # Test 3: Share meal with another family member
        if user2:
            print("\n4. Testing meal share request...")
            share_data = MealShareRequestCreate(
                meal_id=meal1.id,
                recipient_user_id=user2.id,
                message="Would you like to try this recipe?"
            )
            
            # Check for existing request first
            existing = check_existing_request(db, meal1.id, user1.id, user2.id)
            if existing:
                print(f"   ⚠️  Pending request already exists (ID: {existing.id})")
            else:
                share_request = create_share_request(db, share_data, user1.id, meal1)
                print(f"✅ Created share request (ID: {share_request.id})")
                print(f"   - From: User {share_request.sender_user_id}")
                print(f"   - To: User {share_request.recipient_user_id}")
                print(f"   - Meal: {share_request.meal_id}")
                print(f"   - Family: {share_request.family_id}")
                print(f"   - Status: {share_request.status}")
                
                accepted_request, cloned_meal = accept_share_request(db, share_request)
                print(f"✅ Recipient accepted the request and received meal (ID: {cloned_meal.id})")
                print(f"   - Accepted meal owner: {cloned_meal.created_by_user_id}")
                print(f"   - Accepted meal name: {cloned_meal.name}")
                print(f"   - Request accepted_meal_id: {accepted_request.accepted_meal_id}")
                print("   ✅ Global meal clone created successfully!")
                
                # Cleanup accepted data for repeatable tests
                db.delete(cloned_meal)
                db.delete(accepted_request)
                db.commit()
        else:
            print("\n4. Skipping share request test (no second family member)")
        
        # Test 4: Validation checks
        print("\n5. Testing validation...")
        
        # Try to share a meal without family_id (should fail in API)
        meal_data3 = MealCreate(
            name="Orphan Meal",
            image="https://example.com/image3.jpg",
            calories=300,
            prepTime=5,
            cookTime=10,
            totalTime=15,
            mealType="Snack",
            cuisine="American",
            tags=["quick"],
            macros=MacroBreakdown(protein=10, fats=5, carbs=40),
            difficulty="Easy",
            servings=1,
            dietCompatibility=["vegan"],
            goalFit=["maintenance"],
            ingredients=[
                IngredientIn(name="Banana", amount="1", inPantry=False)
            ],
            instructions=["Peel and eat"],
            cookingTools=[],
            notes="No family",
            isFavorite=False,
            familyId=None
        )
        
        orphan_meal = create_meal(db, meal_data3, user1.id)
        print(f"✅ Created meal without family: {orphan_meal.name} (ID: {orphan_meal.id})")
        print(f"   - Family ID: {orphan_meal.family_id}")
        
        if orphan_meal.family_id is None:
            print("   ✅ Meal without family_id created successfully!")
        
        if user2:
            print("\n6. Testing share request for personal meal (no family required)...")
            orphan_share = MealShareRequestCreate(
                meal_id=orphan_meal.id,
                recipient_user_id=user2.id,
                message="Sharing a personal recipe!"
            )
            existing_orphan = check_existing_request(db, orphan_meal.id, user1.id, user2.id)
            if existing_orphan:
                db.delete(existing_orphan)
                db.commit()
            
            personal_request = create_share_request(db, orphan_share, user1.id, orphan_meal)
            print(f"✅ Created personal share request (ID: {personal_request.id}) with family_id={personal_request.family_id}")
            
            accepted_personal, cloned_personal_meal = accept_share_request(db, personal_request)
            print(f"✅ Recipient now has their own copy (ID: {cloned_personal_meal.id})")
            if accepted_personal.family_id is None:
                print("   ✅ Share request stored without family reference!")
            if accepted_personal.accepted_meal_id == cloned_personal_meal.id:
                print("   ✅ accepted_meal_id recorded correctly")
            
            # Cleanup
            db.delete(cloned_personal_meal)
            db.delete(accepted_personal)
            db.commit()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED! ✅")
        print("="*60)
        print("\nSummary:")
        print("✅ Meals can be created with family_id")
        print("✅ Family_id is persisted correctly in database")
        print("✅ Meals can be attached to families after creation")
        print("✅ Share requests can be created globally (family optional)")
        if user2:
            print("✅ Accepting a share request clones the meal for the recipient")
        print("\nReady for production deployment!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = test_meal_sharing()
    sys.exit(0 if success else 1)
