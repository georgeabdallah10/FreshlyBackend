"""
Test script to verify family members API returns properly normalized data.
This should fix the "Unknown User" bug in the frontend.
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
# Replace with a valid token from your system
AUTH_TOKEN = "your_auth_token_here"

def test_family_members():
    """Test the GET /families/{family_id}/members endpoint"""
    
    # First, get list of families
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    
    print("=" * 60)
    print("Testing Family Members API - Data Normalization Fix")
    print("=" * 60)
    
    # Get user's families
    print("\n1. Fetching user's families...")
    families_response = requests.get(f"{BASE_URL}/families", headers=headers)
    
    if families_response.status_code != 200:
        print(f"❌ Failed to fetch families: {families_response.status_code}")
        print(families_response.text)
        return
    
    families = families_response.json()
    print(f"✅ Found {len(families)} family/families")
    
    if not families:
        print("⚠️  No families found. Create a family first.")
        return
    
    # Test each family's members
    for family in families:
        family_id = family['id']
        family_name = family['display_name']
        
        print(f"\n2. Fetching members for family: '{family_name}' (ID: {family_id})")
        print("-" * 60)
        
        members_response = requests.get(
            f"{BASE_URL}/families/{family_id}/members",
            headers=headers
        )
        
        if members_response.status_code != 200:
            print(f"❌ Failed to fetch members: {members_response.status_code}")
            print(members_response.text)
            continue
        
        members = members_response.json()
        print(f"✅ Found {len(members)} member(s)")
        
        # Verify data structure
        print("\n3. Verifying member data structure:")
        for i, member in enumerate(members, 1):
            print(f"\n   Member {i}:")
            print(f"   - ID: {member.get('id')}")
            print(f"   - User ID: {member.get('user_id')}")
            print(f"   - Role: {member.get('role')}")
            print(f"   - Joined At: {member.get('joined_at')}")
            
            # Check for nested user object (this is the fix)
            if 'user' in member and member['user']:
                user = member['user']
                print(f"   - ✅ User Object Found:")
                print(f"     • Name: {user.get('name', 'N/A')}")
                print(f"     • Email: {user.get('email', 'N/A')}")
                print(f"     • Phone: {user.get('phone_number', 'N/A')}")
                print(f"     • Status: {user.get('status', 'N/A')}")
                print(f"     • Avatar: {user.get('avatar_path', 'N/A')}")
            else:
                print(f"   - ❌ Missing user object (this would cause 'Unknown User')")
        
        print("\n" + "=" * 60)
        print("Raw JSON Response:")
        print(json.dumps(members, indent=2))
        print("=" * 60)

if __name__ == "__main__":
    print("\n🔧 Family Members API Test Script")
    print("📝 This verifies the fix for 'Unknown User' bug\n")
    
    # Check if token is set
    if AUTH_TOKEN == "your_auth_token_here":
        print("⚠️  Please set a valid AUTH_TOKEN in the script")
        print("\nTo get a token:")
        print("1. Start the backend: uvicorn main:app --reload")
        print("2. Login via POST /auth/login")
        print("3. Copy the access_token from the response")
        print("4. Update AUTH_TOKEN in this script")
    else:
        test_family_members()
