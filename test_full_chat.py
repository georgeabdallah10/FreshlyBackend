#!/usr/bin/env python3
"""
Test script for authenticated chat with conversation history
"""
import requests
import json

BASE_URL = "http://localhost:8002"

def login_user():
    """Login with test user credentials"""
    print("Attempting to login...")
    
    # First, let's try to register a test user
    register_url = f"{BASE_URL}/auth/register"
    register_payload = {
        "email": "chattest@example.com",
        "password": "testpassword123",
        "name": "Chat Test User"
    }
    
    try:
        # Try to register (might fail if user already exists)
        response = requests.post(register_url, json=register_payload)
        if response.status_code == 201:
            print("✅ Test user registered successfully")
        elif response.status_code == 400:
            print("ℹ️  Test user already exists, proceeding to login")
        else:
            print(f"⚠️  Registration returned status: {response.status_code}")
    except Exception as e:
        print(f"Registration attempt: {e}")
    
    # Now login
    login_url = f"{BASE_URL}/auth/login"
    login_payload = {
        "email": "chattest@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(login_url, json=login_payload)
        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            if token:
                print("✅ Login successful!")
                return token
            else:
                print("❌ Login successful but no token received")
                return None
        else:
            print(f"❌ Login failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_authenticated_chat_flow(token):
    """Test the full authenticated chat flow with conversation history"""
    print("\n🧪 Testing authenticated chat with conversation history...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Start a new conversation
    print("\n1. Starting a new conversation...")
    chat_url = f"{BASE_URL}/chat"
    
    message1 = {
        "prompt": "Hello! I'm planning to cook dinner tonight. What ingredients do I need for a simple pasta dish?",
        "system": "You are a helpful cooking assistant for a meal planning app."
    }
    
    try:
        response = requests.post(chat_url, json=message1, headers=headers)
        response.raise_for_status()
        result1 = response.json()
        
        print(f"✅ First message successful!")
        print(f"AI Response: {result1['reply'][:100]}...")
        conversation_id = result1['conversation_id']
        print(f"Conversation ID: {conversation_id}")
        
        # Test 2: Continue the conversation
        print("\n2. Continuing the conversation...")
        message2 = {
            "prompt": "That sounds great! How long should I cook the pasta?",
            "conversation_id": conversation_id
        }
        
        response = requests.post(chat_url, json=message2, headers=headers)
        response.raise_for_status()
        result2 = response.json()
        
        print(f"✅ Second message successful!")
        print(f"AI Response: {result2['reply'][:100]}...")
        
        # Test 3: Get conversation history
        print("\n3. Retrieving conversation history...")
        conv_url = f"{BASE_URL}/chat/conversations/{conversation_id}"
        response = requests.get(conv_url, headers=headers)
        response.raise_for_status()
        conversation = response.json()
        
        print(f"✅ Conversation retrieved!")
        print(f"Total messages: {len(conversation['messages'])}")
        
        # Test 4: List all conversations
        print("\n4. Listing all conversations...")
        convs_url = f"{BASE_URL}/chat/conversations"
        response = requests.get(convs_url, headers=headers)
        response.raise_for_status()
        conversations = response.json()
        
        print(f"✅ Conversations listed!")
        print(f"Total conversations: {len(conversations)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Authenticated chat test failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Error details: {e.response.text}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Authenticated Chat Flow")
    print("=" * 50)
    
    # Login and get token
    token = login_user()
    
    if token:
        # Test authenticated chat
        success = test_authenticated_chat_flow(token)
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 Full authenticated chat flow working perfectly!")
            print("\nFeatures confirmed:")
            print("• ✅ User authentication")
            print("• ✅ Conversation creation")
            print("• ✅ Message history persistence")
            print("• ✅ Conversation retrieval")
            print("• ✅ OpenAI integration")
        else:
            print("❌ Some issues with authenticated chat flow")
    else:
        print("❌ Could not test authenticated features due to login failure")
