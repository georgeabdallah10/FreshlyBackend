#!/bin/bash

# Quick fix deployment for 500 error in meal share requests
# This script MUST run the database migration

set -e

echo "================================================"
echo "500 ERROR FIX - MEAL SHARE REQUESTS"
echo "================================================"
echo ""
echo "ROOT CAUSE: meal_share_requests table doesn't exist!"
echo "FIX: Run database migration"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Step 1: Commit code changes
echo "Step 1: Committing code changes..."
echo "-----------------------------------"

git add .
git commit -m "fix: resolve 500 error in meal share requests - add proper schema and error handling

- Fixed MealShareRequestOut schema to use serialization_alias
- Added proper error handling in meal_share_requests router
- Use model_validate() for response construction
- Added logging for debugging
- Root cause: meal_share_requests table doesn't exist (migration needed)"

git push origin main
print_success "Code pushed to repository"

# Step 2: Deploy to production
echo ""
echo "Step 2: Deploying to production..."
echo "-----------------------------------"
echo ""
print_warning "CRITICAL: This will run the database migration!"
echo ""
read -p "Continue with deployment? (yes/no) " -r
echo

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    print_error "Deployment cancelled"
    exit 1
fi

# SSH and deploy
ssh root@freshlybackend.duckdns.org << 'EOF'
set -e

echo "→ Navigating to project directory..."
cd /root/FreshlyBackend

echo "→ Pulling latest code..."
git pull origin main

echo "→ Activating virtual environment..."
source .venv/bin/activate

echo ""
echo "→ Running database migration (CRITICAL STEP)..."
echo "================================================"
alembic upgrade head
echo "================================================"
echo ""

echo "→ Checking migration status..."
alembic current

echo ""
echo "→ Restarting service..."
systemctl restart freshly-backend

echo "→ Waiting for service to start..."
sleep 3

echo "→ Checking service status..."
systemctl status freshly-backend --no-pager | head -15

echo ""
echo "→ Recent logs:"
journalctl -u freshly-backend -n 20 --no-pager

EOF

print_success "Deployment complete!"

# Step 3: Test the fix
echo ""
echo "Step 3: Testing the fix..."
echo "-----------------------------------"
echo ""
echo "Please test the following:"
echo ""
echo "1. Create share request:"
echo "   POST https://freshlybackend.duckdns.org/meal-share-requests"
echo "   Body: {\"mealId\": 13, \"recipientUserId\": 52}"
echo ""
echo "2. Expected: 201 Created with full share request object"
echo ""
echo "3. Check database:"
echo "   SELECT * FROM meal_share_requests;"
echo ""

print_success "Fix deployment complete!"
echo ""
echo "================================================"
echo "NEXT STEPS:"
echo "1. Test the endpoint with Postman/frontend"
echo "2. Verify 201 response (not 500)"
echo "3. Check that record is created in database"
echo "4. Notify frontend team that bug is fixed"
echo "================================================"
