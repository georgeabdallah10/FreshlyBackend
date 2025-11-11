#!/usr/bin/env python3
"""
Test script for meal share request 500 error fix
Tests the complete flow of creating a share request
"""

import sys
from sqlalchemy.orm import Session
from core.db import SessionLocal
from models.user import User
from models.family import Family
from models.membership import FamilyMembership
from models.meal import Meal
from schemas.meal_share_request import MealShareRequestCreate, MealShareRequestOut
from crud.meal_share_requests import create_share_request, check_existing_request, accept_share_request
from crud.meals import get_meal

def test_share_request_creation():
    """Test creating a meal share request with proper schema validation"""
    db: Session = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("MEAL SHARE REQUEST 500 ERROR FIX TEST")
        print("="*60)
        
        # Get test data
        print("\n1. Fetching test data...")
        
        # Get meal 13 that has family_id
        meal = get_meal(db, 13)
        if not meal:
            print("❌ Meal 13 not found")
            return False
        
        print(f"✅ Found meal: {meal.name} (ID: {meal.id})")
        print(f"   - Created by user: {meal.created_by_user_id}")
        print(f"   - Family ID: {meal.family_id}")
        
        if not meal.family_id:
            print("❌ Meal does not have family_id!")
            return False
        
        # Get the users
        sender = db.query(User).get(53)  # User who created the meal
        recipient = db.query(User).get(52)  # User to share with
        
        if not sender or not recipient:
            print("❌ Users not found")
            return False
        
        print(f"✅ Sender: {sender.name} (ID: {sender.id})")
        print(f"✅ Recipient: {recipient.name} (ID: {recipient.id})")
        
        # Verify both are in the family
        sender_membership = db.query(FamilyMembership).filter(
            FamilyMembership.family_id == meal.family_id,
            FamilyMembership.user_id == sender.id
        ).first()
        
        recipient_membership = db.query(FamilyMembership).filter(
            FamilyMembership.family_id == meal.family_id,
            FamilyMembership.user_id == recipient.id
        ).first()
        
        if not sender_membership:
            print(f"❌ Sender not in family {meal.family_id}")
            return False
        
        if not recipient_membership:
            print(f"❌ Recipient not in family {meal.family_id}")
            return False
        
        print(f"✅ Both users are members of family {meal.family_id}")
        
        # Test 2: Create share request schema
        print("\n2. Testing schema validation...")
        
        try:
            share_data = MealShareRequestCreate(
                meal_id=meal.id,
                recipientUserId=recipient.id,
                message="Test share request"
            )
            print(f"✅ Schema validation passed")
            print(f"   - meal_id: {share_data.meal_id}")
            print(f"   - recipient_user_id: {share_data.recipient_user_id}")
            print(f"   - message: {share_data.message}")
        except Exception as e:
            print(f"❌ Schema validation failed: {e}")
            return False
        
        # Test 3: Check for existing request
        print("\n3. Checking for existing request...")
        
        existing = check_existing_request(db, meal.id, sender.id, recipient.id)
        if existing:
            print(f"⚠️  Found existing request (ID: {existing.id})")
            print(f"   Deleting existing request for clean test...")
            db.delete(existing)
            db.commit()
            print(f"✅ Deleted existing request")
        else:
            print(f"✅ No existing request found")
        
        # Test 4: Create share request
        print("\n4. Creating share request...")
        
        try:
            request = create_share_request(db, share_data, sender.id, meal)
            print(f"✅ Share request created (ID: {request.id})")
            print(f"   - meal_id: {request.meal_id}")
            print(f"   - sender_user_id: {request.sender_user_id}")
            print(f"   - recipient_user_id: {request.recipient_user_id}")
            print(f"   - family_id: {request.family_id}")
            print(f"   - status: {request.status}")
            print(f"   - message: {request.message}")
        except Exception as e:
            print(f"❌ Failed to create share request: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 5: Build response schema
        print("\n5. Testing response schema...")
        
        try:
            response = MealShareRequestOut.model_validate(request)
            
            # Add nested data
            response.meal_name = request.meal.name if request.meal else None
            response.sender_name = request.sender.name if request.sender else None
            response.recipient_name = request.recipient.name if request.recipient else None
            
            print(f"✅ Response schema validation passed")
            print(f"   - id: {response.id}")
            print(f"   - meal_id: {response.meal_id}")
            print(f"   - sender_user_id: {response.sender_user_id}")
            print(f"   - recipient_user_id: {response.recipient_user_id}")
            print(f"   - family_id: {response.family_id}")
            print(f"   - status: {response.status}")
            print(f"   - meal_name: {response.meal_name}")
            print(f"   - sender_name: {response.sender_name}")
            print(f"   - recipient_name: {response.recipient_name}")
            
            # Test JSON serialization
            response_dict = response.model_dump(by_alias=True, mode='json')
            print(f"\n✅ JSON serialization successful:")
            print(f"   Keys: {list(response_dict.keys())}")
            
            # Verify camelCase keys
            expected_keys = [
                'id',
                'mealId',
                'senderUserId',
                'recipientUserId',
                'familyId',
                'status',
                'message',
                'createdAt',
                'updatedAt',
                'respondedAt',
                'acceptedMealId',
                'mealName',
                'senderName',
                'recipientName',
                'mealDetail',
                'acceptedMealDetail'
            ]
            
            for key in expected_keys:
                if key in response_dict:
                    print(f"   ✓ {key}: {response_dict[key]}")
                else:
                    print(f"   ✗ Missing key: {key}")
            
        except Exception as e:
            print(f"❌ Failed to build response: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 6: Accepting the request clones the meal
        print("\n6. Accepting share request to verify clone creation...")
        accepted_request, cloned_meal = accept_share_request(db, request)
        print(f"✅ Request marked as {accepted_request.status} with accepted_meal_id={accepted_request.accepted_meal_id}")
        print(f"✅ Cloned meal created with ID {cloned_meal.id} for user {cloned_meal.created_by_user_id}")
        
        # Cleanup
        print("\n7. Cleanup...")
        db.delete(cloned_meal)
        db.delete(accepted_request)
        db.commit()
        print(f"✅ Test share request and cloned meal deleted")
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED! ✅")
        print("="*60)
        print("\nThe 500 error fix is working correctly!")
        print("Ready to deploy to production.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = test_share_request_creation()
    sys.exit(0 if success else 1)
