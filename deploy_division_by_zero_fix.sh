#!/bin/bash

# Division by Zero Bug Fix Deployment Script
# Date: December 9, 2025
# Fix: Add validation to prevent division by zero in parse_amount_string()

set -e  # Exit on error

echo "=========================================="
echo "Division by Zero Bug Fix Deployment"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verify we're in the right directory
echo "Step 1: Verifying directory..."
if [ ! -f "services/grocery_calculator.py" ]; then
    echo -e "${RED}Error: Not in FreshlyBackend directory${NC}"
    exit 1
fi
echo -e "${GREEN}✓ In correct directory${NC}"
echo ""

# 2. Show the changes
echo "Step 2: Changes to be deployed..."
echo "-----------------------------------"
echo "File: services/grocery_calculator.py"
echo "Change: Added division by zero validation in parse_amount_string()"
echo ""
git diff services/grocery_calculator.py || echo "No git diff available"
echo ""

# 3. Run verification test
echo "Step 3: Running verification test..."
python test_division_by_zero_fix.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed - aborting deployment${NC}"
    exit 1
fi
echo ""

# 4. Check for compilation errors
echo "Step 4: Checking for errors..."
# This would use your linter/type checker if available
# For now, just try to import the module
python -c "from services.grocery_calculator import parse_amount_string; print('Import successful')"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ No import errors${NC}"
else
    echo -e "${RED}✗ Import failed - aborting deployment${NC}"
    exit 1
fi
echo ""

# 5. Prompt for confirmation
echo "=========================================="
echo "Ready to deploy bug fix"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Commit the division by zero fix"
echo "  2. Push to origin/main"
echo "  3. (You'll need to restart the backend service manually)"
echo ""
read -p "Continue with deployment? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi
echo ""

# 6. Git operations
echo "Step 5: Committing changes..."
git add services/grocery_calculator.py
git add DIVISION_BY_ZERO_BUG_FIX.md
git add ERROR_INVESTIGATION_SUMMARY.md
git add test_division_by_zero_fix.py
git add test_edge_cases_and_bugs.py

git commit -m "Fix: Add division by zero validation in parse_amount_string()

- Prevents crash when parsing fractions with zero denominator (e.g., '1/0')
- Returns (None, None) for invalid fractions (consistent with existing behavior)
- Adds warning log for debugging
- No breaking changes
- Includes comprehensive testing and documentation

Fixes potential server crash on malformed fraction input.
See DIVISION_BY_ZERO_BUG_FIX.md for details."

echo -e "${GREEN}✓ Changes committed${NC}"
echo ""

# 7. Push to remote
echo "Step 6: Pushing to origin/main..."
git push origin main
echo -e "${GREEN}✓ Pushed to remote${NC}"
echo ""

# 8. Final instructions
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. SSH into production server"
echo "  2. Pull latest changes: git pull origin main"
echo "  3. Restart backend service:"
echo "     - systemctl restart freshly-backend"
echo "     - OR docker-compose restart backend"
echo "     - OR your specific restart command"
echo ""
echo "Verification:"
echo "  - Check logs for any startup errors"
echo "  - Test adding items with fractions to grocery list"
echo "  - Monitor for division errors (should be none)"
echo ""
echo -e "${YELLOW}Note: This is a defensive fix. Impact is minimal.${NC}"
echo ""

# 9. Create deployment tag (optional)
read -p "Create deployment tag? (yes/no): " tag_confirm
if [ "$tag_confirm" = "yes" ]; then
    TAG_NAME="bugfix-division-by-zero-$(date +%Y%m%d)"
    git tag -a "$TAG_NAME" -m "Division by zero bug fix in parse_amount_string()"
    git push origin "$TAG_NAME"
    echo -e "${GREEN}✓ Created tag: $TAG_NAME${NC}"
fi

echo ""
echo -e "${GREEN}All done!${NC}"
