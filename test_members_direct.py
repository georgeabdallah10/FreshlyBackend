#!/usr/bin/env python3
"""Quick test to verify family members endpoint returns nested user data"""
import sys
import os

# Add backend to path
sys.path.insert(0, '/Users/georgeabdallah/Documents/GitHub/FreshlyBackend')

from core.db import get_db, engine
from crud.families import list_members
from models.membership import FamilyMembership
from sqlalchemy.orm import Session

def test_list_members():
    """Test the list_members function directly"""
    print("\n" + "="*70)
    print("Testing list_members CRUD function")
    print("="*70 + "\n")
    
    # Get a database session
    db = next(get_db())
    
    try:
        # Test with family_id = 7 (from the debug output)
        family_id = 7
        print(f"Fetching members for family_id: {family_id}")
        
        members = list_members(db, family_id)
        
        print(f"✅ Found {len(members)} members\n")
        
        if not members:
            print("⚠️  No members found")
            return
        
        # Analyze first member
        first_member = members[0]
        print(f"First member object type: {type(first_member)}")
        print(f"First member dict keys: {first_member.__dict__.keys()}\n")
        
        # Check for user relationship
        print("Checking user relationship:")
        if hasattr(first_member, 'user'):
            user = first_member.user
            print(f"✅ Has 'user' attribute")
            print(f"   User type: {type(user)}")
            if user:
                print(f"   User ID: {user.id}")
                print(f"   User name: {user.name}")
                print(f"   User email: {user.email}")
                print(f"   User phone: {user.phone_number}")
            else:
                print(f"   ❌ User is None/null")
        else:
            print(f"❌ Missing 'user' attribute")
        
        # Try serializing to dict
        print("\n\nTrying Pydantic serialization:")
        from schemas.membership import MembershipOut
        
        for i, member in enumerate(members):
            try:
                serialized = MembershipOut.model_validate(member)
                print(f"\n✅ Member {i} serialized successfully")
                print(f"   ID: {serialized.id}")
                print(f"   User ID: {serialized.user_id}")
                print(f"   Role: {serialized.role}")
                print(f"   User object: {serialized.user is not None}")
                if serialized.user:
                    print(f"   User name: {serialized.user.name}")
                    print(f"   User email: {serialized.user.email}")
            except Exception as e:
                print(f"\n❌ Member {i} serialization failed: {e}")
                
    finally:
        db.close()

if __name__ == "__main__":
    test_list_members()
