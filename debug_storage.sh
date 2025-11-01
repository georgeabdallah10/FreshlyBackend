#!/bin/bash

# Test script to debug the storage endpoint issue

echo "🔍 Testing Storage Endpoint Debug"
echo "=================================="

echo "1. Testing health endpoint..."
curl -s https://freshlybackend.duckdns.org/health | jq '.'

echo -e "\n2. Testing OPTIONS preflight..."
curl -X OPTIONS -H "Origin: https://freshly-app-frontend.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  https://freshlybackend.duckdns.org/storage/avatar/proxy -w "\nStatus: %{http_code}\n"

echo -e "\n3. Testing POST with invalid token (to see error format)..."
curl -X POST \
  -H "Authorization: Bearer invalid_token" \
  -F "file=@/dev/null" \
  https://freshlybackend.duckdns.org/storage/avatar/proxy -w "\nStatus: %{http_code}\n"

echo -e "\n4. Testing POST without Authorization header..."
curl -X POST \
  -F "file=@/dev/null" \
  https://freshlybackend.duckdns.org/storage/avatar/proxy -w "\nStatus: %{http_code}\n"

echo -e "\n🔍 Debug complete. Check the error messages above."
