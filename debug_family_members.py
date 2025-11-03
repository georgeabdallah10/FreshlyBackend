#!/usr/bin/env python3
"""
Debugging script to verify the family members API returns nested user data correctly.
This will help identify if the issue is with the database query, schema, or serialization.
"""

import requests
import json
import sys
from typing import Optional

# Configuration
BASE_URL = "https://freshlybackend.duckdns.org"  # Change to production URL if needed

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_success(msg: str):
    """Print success message"""
    print(f"✅ {msg}")

def print_error(msg: str):
    """Print error message"""
    print(f"❌ {msg}")

def print_warning(msg: str):
    """Print warning message"""
    print(f"⚠️  {msg}")

def get_auth_token() -> Optional[str]:
    """Get authentication token from user"""
    token = input("Enter your authentication token (or press Enter to skip): ").strip()
    return token if token else None

def test_api_health():
    """Test if API is running"""
    print_section("Testing API Health")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"API is running at {BASE_URL}")
            return True
        else:
            print_error(f"API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to API at {BASE_URL}")
        print_warning("Make sure the backend is running: uvicorn main:app --reload")
        return False

def test_family_members_endpoint(family_id: int, token: Optional[str]):
    """Test the family members endpoint"""
    print_section(f"Testing GET /families/{family_id}/members")
    
    if not token:
        print_warning("No auth token provided, skipping test")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/families/{family_id}/members"
    
    print(f"Request URL: {url}")
    print(f"Headers: Authorization: Bearer {token[:20]}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
        
        if response.status_code == 200:
            data = response.json()
            
            print_success("API returned 200 OK")
            print(f"\nNumber of members: {len(data)}")
            
            # Pretty print the JSON response
            print("\n--- RAW RESPONSE ---")
            print(json.dumps(data, indent=2, default=str))
            
            # Analyze the response structure
            print("\n--- ANALYSIS ---")
            analyze_response(data)
            
        elif response.status_code == 401:
            print_error("Unauthorized - invalid or expired token")
        elif response.status_code == 403:
            print_error("Forbidden - insufficient permissions (must be family member)")
        elif response.status_code == 404:
            print_error(f"Family {family_id} not found")
        else:
            print_error(f"Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print_error("Request timed out - API might be slow or unresponsive")
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
    except json.JSONDecodeError:
        print_error("Response is not valid JSON")

def analyze_response(data):
    """Analyze the response structure"""
    if not isinstance(data, list):
        print_error("Response is not an array")
        return
    
    if len(data) == 0:
        print_warning("No members returned")
        return
    
    first_member = data[0]
    print(f"First member keys: {list(first_member.keys())}")
    
    # Check for required fields
    required_fields = {
        "id": "Membership ID",
        "family_id": "Family ID",
        "user_id": "User ID",
        "role": "Role (owner/member)",
    }
    
    missing_fields = []
    for field, description in required_fields.items():
        if field in first_member:
            print_success(f"✓ Has '{field}' ({description}): {first_member[field]}")
        else:
            print_error(f"✗ Missing '{field}' ({description})")
            missing_fields.append(field)
    
    # Check for nested user object
    if "user" in first_member:
        user = first_member["user"]
        if isinstance(user, dict):
            print_success("✓ Has nested 'user' object")
            
            user_fields = {
                "id": "User ID",
                "name": "User name",
                "email": "User email",
                "phone_number": "User phone",
                "avatar_path": "User avatar",
            }
            
            for field, description in user_fields.items():
                if field in user:
                    value = user[field]
                    if value:
                        print_success(f"  ✓ user.{field}: {value}")
                    else:
                        print_warning(f"  ⚠ user.{field}: null/empty")
                else:
                    print_error(f"  ✗ Missing user.{field}")
        else:
            print_error(f"✗ 'user' field is not an object, it's a {type(user).__name__}")
    else:
        print_error("✗ Missing 'user' object (CRITICAL - this is the main issue)")
    
    # Check for joined_at
    if "joined_at" in first_member:
        print_success(f"✓ Has 'joined_at': {first_member['joined_at']}")
    else:
        print_warning("⚠ Missing 'joined_at'")
    
    # Check for unexpected fields (might indicate old schema)
    unexpected_fields = ["email", "name", "phone", "status"]
    found_unexpected = [f for f in unexpected_fields if f in first_member]
    if found_unexpected:
        print_error(f"✗ Unexpected fields (old schema?): {found_unexpected}")
        print_warning("This indicates the response is using an old schema instead of nested user object")

def get_list_of_families(token: Optional[str]):
    """Get list of families user belongs to"""
    print_section("Getting Your Families")
    
    if not token:
        print_warning("No auth token provided, skipping")
        return []
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/families"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            families = response.json()
            print_success(f"Found {len(families)} family/families")
            
            for fam in families:
                print(f"\n  Family ID: {fam.get('id')}")
                print(f"  Name: {fam.get('display_name')}")
                print(f"  Invite Code: {fam.get('invite_code')}")
            
            return families
        else:
            print_error(f"Failed to get families: {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error: {e}")
        return []

def main():
    """Main function"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   Family Members API - Debugging Script                           ║
║   This script helps identify the nested user data bug             ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
    """)
    
    # Test API health
    if not test_api_health():
        sys.exit(1)
    
    # Get auth token
    print_section("Authentication")
    token = get_auth_token()
    
    if not token:
        print_warning("Skipping authenticated tests")
        sys.exit(0)
    
    # Get families
    families = get_list_of_families(token)
    
    if not families:
        print_error("No families found or unable to fetch")
        sys.exit(1)
    
    # Test family members endpoint
    family_id = families[0]["id"]
    test_family_members_endpoint(family_id, token)
    
    # Summary
    print_section("Summary")
    print("""
WHAT TO CHECK IN THE RESPONSE:

1. ✓ Response includes nested 'user' object (not flattened fields)
2. ✓ user.id, user.name, user.email, user.phone_number are all present
3. ✓ Response is consistent across multiple calls
4. ✓ Owner's user data is NOT empty

IF YOU SEE OLD RESPONSE STRUCTURE:
- Fields like "email", "name", "phone" at root level (not in user object)
- Missing nested "user" object
- Status: "Unknown Member" fallback needed

ACTION ITEMS:
- Check crud/families.py list_members() has joinedload
- Check schemas/membership.py has 'user: UserOut' field
- Check schemas/user.py has 'from_attributes = True'
- Restart the FastAPI server
- Try again
    """)

if __name__ == "__main__":
    main()
