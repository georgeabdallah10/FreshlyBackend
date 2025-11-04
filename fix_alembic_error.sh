#!/bin/bash

# Fix Alembic migration error by removing empty migration file

echo "================================================"
echo "FIXING ALEMBIC MIGRATION ERROR"
echo "================================================"
echo ""
echo "Problem: Empty migration file breaking Alembic"
echo "File: d36abaa2f689_add_shared_with_family_to_meals.py"
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

# Check if file exists locally
if [ -f "migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py" ]; then
    echo "→ Found empty migration file locally"
    
    # Check if it's empty
    if [ ! -s "migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py" ]; then
        print_warning "File is empty - removing it"
        rm migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py
        print_success "Deleted empty migration file locally"
        
        # Commit the deletion
        git add migrations/versions/
        git commit -m "fix: remove empty migration file breaking Alembic"
        git push origin main
        print_success "Changes pushed to repository"
    else
        print_error "File is not empty - manual review needed"
        exit 1
    fi
else
    print_warning "File not found locally (may only exist in production)"
fi

# Fix in production
echo ""
echo "→ Fixing in production..."
print_warning "This will SSH to production and remove the empty file"
echo ""
read -p "Continue? (yes/no) " -r
echo

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    print_error "Cancelled"
    exit 1
fi

ssh root@freshlybackend.duckdns.org << 'EOF'
set -e

echo "→ Navigating to project directory..."
cd /root/FreshlyBackend

echo "→ Checking for empty migration file..."
if [ -f "migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py" ]; then
    if [ ! -s "migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py" ]; then
        echo "→ Found empty file - removing it..."
        rm migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py
        echo "✅ Deleted empty migration file"
    else
        echo "⚠️  File is not empty - skipping"
    fi
else
    echo "ℹ️  File doesn't exist (already removed or git pull needed)"
fi

echo ""
echo "→ Pulling latest code (to get the fix)..."
git pull origin main

echo "→ Activating virtual environment..."
source .venv/bin/activate

echo ""
echo "→ Testing Alembic..."
alembic current

echo ""
echo "→ Running migrations..."
alembic upgrade head

echo ""
echo "→ Checking final migration status..."
alembic current

echo ""
echo "→ Restarting service..."
systemctl restart freshly-backend

echo "→ Service status..."
systemctl status freshly-backend --no-pager | head -10

EOF

print_success "Fix complete!"

echo ""
echo "================================================"
echo "ALEMBIC FIXED & MIGRATIONS RUN"
echo "================================================"
echo ""
echo "Next: Test the meal share requests endpoint"
echo "POST /meal-share-requests should now work!"
echo ""
