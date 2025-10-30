#!/usr/bin/env python3
"""
Simple test script for the chat API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8002"

def test_legacy_chat():
    """Test the legacy chat endpoint (no authentication required)"""
    print("Testing legacy chat endpoint...")
    
    url = f"{BASE_URL}/chat/legacy"
    payload = {
        "prompt": "Hello! Can you tell me what 2+2 equals?",
        "system": "You are a helpful math tutor."
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ Legacy chat successful!")
        print(f"Response: {result['reply']}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Legacy chat failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Error details: {e.response.text}")
        return False

def test_authenticated_chat():
    """Test the authenticated chat endpoint (requires login)"""
    print("\nTesting authenticated chat endpoint...")
    print("Note: This requires user authentication, so we'll just check if the endpoint exists")
    
    url = f"{BASE_URL}/chat"
    payload = {
        "prompt": "Hello! Tell me about cooking.",
        "system": "You are a cooking assistant."
    }
    
    try:
        # This should return 401 Unauthorized since we're not authenticated
        response = requests.post(url, json=payload)
        if response.status_code == 401:
            print("✅ Authenticated endpoint exists and properly requires authentication")
            return True
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing authenticated endpoint: {e}")
        return False

def test_conversations_endpoints():
    """Test the conversations endpoints"""
    print("\nTesting conversation endpoints...")
    
    endpoints_to_test = [
        "/chat/conversations",
        "/chat/conversations/1",
        "/chat/conversations/1/messages"
    ]
    
    for endpoint in endpoints_to_test:
        url = f"{BASE_URL}{endpoint}"
        try:
            response = requests.get(url)
            if response.status_code == 401:
                print(f"✅ {endpoint} exists and properly requires authentication")
            else:
                print(f"⚠️  {endpoint} returned unexpected status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error testing {endpoint}: {e}")

if __name__ == "__main__":
    print("🧪 Testing Chat API Endpoints")
    print("=" * 50)
    
    # Test legacy endpoint (should work without auth)
    legacy_success = test_legacy_chat()
    
    # Test authenticated endpoints (should require auth)
    auth_success = test_authenticated_chat()
    test_conversations_endpoints()
    
    print("\n" + "=" * 50)
    if legacy_success:
        print("🎉 Chat API is working! OpenAI integration successful!")
        print("\nYou can now use:")
        print("• /chat/legacy - for simple chat without history")
        print("• /chat - for authenticated chat with conversation history")
        print("• /chat/conversations - to list user conversations")
        print("• /chat/conversations/{id} - to get a specific conversation")
    else:
        print("❌ There were issues with the chat API")
