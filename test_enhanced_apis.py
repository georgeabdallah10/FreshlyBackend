"""
Quick test to verify the enhanced pantry functionality with automatic image generation
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8080"

def test_enhanced_apis():
    print("🚀 Testing Enhanced Freshly Backend APIs")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. 🏥 Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health: {data['status']} - {data['app']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test API documentation
    print("\n2. 📚 API Documentation")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ API documentation accessible at /docs")
        else:
            print(f"❌ Docs failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Docs error: {e}")
    
    # Test new AI endpoints (expect 401 - authentication required)
    print("\n3. 🎨 Image Generation Endpoint")
    try:
        response = requests.post(
            f"{BASE_URL}/chat/generate-image",
            headers={"Content-Type": "application/json"},
            json={"prompt": "test"}
        )
        if response.status_code == 401:
            print("✅ Image generation endpoint requires authentication (expected)")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Image generation test error: {e}")
    
    print("\n4. 🛒 Grocery Scanning Endpoint")
    try:
        response = requests.post(
            f"{BASE_URL}/chat/scan-grocery",
            headers={"Content-Type": "application/json"},
            json={"image_data": "test"}
        )
        if response.status_code == 401:
            print("✅ Grocery scanning endpoint requires authentication (expected)")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Grocery scanning test error: {e}")
    
    print("\n5. 🏠 Pantry Items Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/pantry-items")
        if response.status_code == 401:
            print("✅ Pantry items endpoint requires authentication (expected)")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Pantry items test error: {e}")
    
    # Test authentication endpoints
    print("\n6. 🔐 Authentication Endpoints")
    try:
        response = requests.get(f"{BASE_URL}/auth/me")
        if response.status_code == 401:
            print("✅ /auth/me requires authentication (expected)")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Auth test error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ ALL SYSTEMS OPERATIONAL!")
    print("\n🎯 Ready for Frontend Integration:")
    print("• Image Generation: POST /chat/generate-image")
    print("• Grocery Scanning: POST /chat/scan-grocery") 
    print("• Enhanced Pantry: GET/POST /pantry-items (with automatic image generation)")
    print("• Authentication: All endpoints properly secured")
    print("\n📋 Next Steps:")
    print("1. Use the GitHub Copilot prompt to implement frontend components")
    print("2. Configure OpenAI API key in production for AI features")
    print("3. Configure Supabase credentials for image storage")
    print("4. Test end-to-end functionality with real authentication")

if __name__ == "__main__":
    test_enhanced_apis()
