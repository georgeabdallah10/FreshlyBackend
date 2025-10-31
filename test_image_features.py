"""
Test script for the new image generation and grocery scanning features
"""
import requests
import base64
import json


# Test configuration
BASE_URL = "http://127.0.0.1:8080"
# In production, you would get this token from a login request
TEST_TOKEN = "your_jwt_token_here"  # Replace with actual token

headers = {
    "Authorization": f"Bearer {TEST_TOKEN}",
    "Content-Type": "application/json"
}


def test_image_generation():
    """Test the image generation endpoint"""
    print("🎨 Testing Image Generation...")
    
    payload = {
        "prompt": "A cozy kitchen with fresh vegetables on the counter, warm lighting, modern appliances",
        "size": "1024x1024",
        "quality": "hd",
        "style": "natural"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/generate-image",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Image generated successfully!")
            print(f"🖼️  Image URL: {result['image_url']}")
            print(f"💬 Conversation ID: {result['conversation_id']}")
            print(f"📝 Message ID: {result['message_id']}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def test_grocery_scanning():
    """Test the grocery scanning endpoint"""
    print("\n🛒 Testing Grocery Scanning...")
    
    # Create a sample base64 image (in practice, this would be a real photo)
    # This is just a placeholder - you'd convert an actual image file
    sample_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    payload = {
        "image_data": sample_image_data
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/scan-grocery",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Grocery scan completed!")
            print(f"🔢 Total items found: {result['total_items']}")
            print(f"💬 Conversation ID: {result['conversation_id']}")
            print(f"📝 Message ID: {result['message_id']}")
            
            if result['items']:
                print("\n📋 Identified Items:")
                for item in result['items']:
                    print(f"  • {item['name']}")
                    print(f"    Quantity: {item['quantity']}")
                    print(f"    Category: {item['category']}")
                    print(f"    Confidence: {item['confidence']:.2f}")
                    print()
            
            if result['analysis_notes']:
                print(f"📝 AI Notes: {result['analysis_notes']}")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


def demo_usage_without_auth():
    """Demonstrate the API structure without authentication"""
    print("\n📚 API Endpoint Documentation:")
    print("\n🎨 Image Generation:")
    print("POST /chat/generate-image")
    print("Payload example:")
    print(json.dumps({
        "prompt": "A beautiful garden with fresh herbs and vegetables",
        "size": "1024x1024",
        "quality": "hd", 
        "style": "natural",
        "conversation_id": None  # Optional - creates new conversation if not provided
    }, indent=2))
    
    print("\n🛒 Grocery Scanning:")
    print("POST /chat/scan-grocery")
    print("Payload example:")
    print(json.dumps({
        "image_data": "base64_encoded_image_string",
        "conversation_id": None  # Optional - creates new conversation if not provided
    }, indent=2))
    
    print("\n📋 Expected Response for Grocery Scanning:")
    print(json.dumps({
        "items": [
            {
                "name": "Red Delicious Apples",
                "quantity": "3 pieces",
                "category": "fruits",
                "confidence": 0.95
            },
            {
                "name": "Whole Milk",
                "quantity": "1 gallon",
                "category": "dairy",
                "confidence": 0.88
            }
        ],
        "total_items": 2,
        "analysis_notes": "Good image quality, all items clearly visible",
        "conversation_id": 123,
        "message_id": 456
    }, indent=2))


if __name__ == "__main__":
    print("🚀 Freshly Backend - Image Features Test")
    print("=" * 50)
    
    # Test without actual authentication for demo purposes
    demo_usage_without_auth()
    
    print("\n" + "=" * 50)
    print("💡 To test with real authentication:")
    print("1. Register/login to get a JWT token")
    print("2. Set the TEST_TOKEN variable above")
    print("3. Ensure OpenAI API key is configured in settings")
    print("4. Run the test functions")
    
    # Uncomment these lines when you have proper authentication:
    # test_image_generation()
    # test_grocery_scanning()
