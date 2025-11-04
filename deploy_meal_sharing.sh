#!/bin/bash

# Meal Sharing System Deployment Script
# This script deploys the meal sharing feature to production

set -e  # Exit on any error

echo "=========================================="
echo "MEAL SHARING SYSTEM DEPLOYMENT"
echo "=========================================="
echo ""

# Configuration
REMOTE_USER="your_user"  # UPDATE THIS
REMOTE_HOST="your_server"  # UPDATE THIS
REMOTE_PATH="/path/to/FreshlyBackend"  # UPDATE THIS
SERVICE_NAME="freshly-backend"  # UPDATE THIS

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Local checks
echo "Step 1: Running local checks..."
echo "--------------------------------"

# Check if git is clean
if [[ -n $(git status -s) ]]; then
    print_warning "You have uncommitted changes"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "Git working directory is clean"
fi

# Check if migration file exists
if [ -f "migrations/versions/ec785f0856c7_add_meal_share_requests_table_remove_.py" ]; then
    print_success "Migration file found"
else
    print_error "Migration file not found!"
    exit 1
fi

# Step 2: Commit and push changes
echo ""
echo "Step 2: Git operations..."
echo "-------------------------"

read -p "Do you want to commit and push changes? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git add .
    git commit -m "feat: implement meal sharing system with family support" || true
    git push origin main
    print_success "Changes pushed to repository"
else
    print_warning "Skipping git operations"
fi

# Step 3: Production deployment
echo ""
echo "Step 3: Deploying to production..."
echo "-----------------------------------"

read -p "Deploy to production? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Deployment cancelled"
    exit 0
fi

# SSH commands
ssh $REMOTE_USER@$REMOTE_HOST << 'ENDSSH'
set -e

echo "→ Navigating to project directory..."
cd $REMOTE_PATH

echo "→ Pulling latest changes..."
git pull origin main

echo "→ Activating virtual environment..."
source venv/bin/activate || source env/bin/activate

echo "→ Installing dependencies (if any)..."
pip install -r requirements.txt --quiet

echo "→ Running database migrations..."
alembic upgrade head

echo "→ Checking migration status..."
alembic current

echo "→ Restarting service..."
sudo systemctl restart $SERVICE_NAME || sudo supervisorctl restart $SERVICE_NAME

echo "→ Checking service status..."
sleep 3
sudo systemctl status $SERVICE_NAME --no-pager || sudo supervisorctl status $SERVICE_NAME

ENDSSH

print_success "Deployment complete!"

# Step 4: Verification
echo ""
echo "Step 4: Verification..."
echo "------------------------"
echo ""
echo "Please test the following endpoints:"
echo ""
echo "1. Create meal with family:"
echo "   POST /meals/me with familyId in body"
echo ""
echo "2. Attach family to meal:"
echo "   POST /meals/{meal_id}/attach-family"
echo ""
echo "3. Share meal:"
echo "   POST /meal-share-requests"
echo ""
echo "See MEAL_SHARING_DEPLOYMENT_GUIDE.md for detailed test examples."
echo ""
print_success "Deployment script finished!"
echo ""
echo "=========================================="
