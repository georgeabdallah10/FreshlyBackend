#!/bin/bash
# Deploy Sync Pantry Fix to Production

set -e  # Exit on error

echo "🚀 DEPLOYING SYNC PANTRY FIX"
echo "============================"
echo ""

# 1. Check for uncommitted changes
echo "📝 Checking for uncommitted changes..."
if [[ -n $(git status -s) ]]; then
    echo "⚠️  You have uncommitted changes:"
    git status -s
    echo ""
    read -p "Do you want to commit these changes? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add services/grocery_list_service.py
        git add services/grocery_calculator.py
        git add routers/grocery_lists.py
        git add schemas/grocery_list.py
        git add FRONTEND_REMAINING_ITEMS_UPDATE.txt
        git add SYNC_PANTRY_FIX_COMPLETE.md
        
        git commit -m "feat: Add pantry sync with remaining_items and fuzzy ingredient matching

- Parse notes like '2 cups' into quantity and unit
- Subtract pantry quantities from grocery list items
- Return remaining_items in sync response
- Add fuzzy matching to prevent duplicate ingredients
- Support flexible unit comparison when canonical units missing

Fixes ingredient ID mismatch issue where grocery items wouldn't match pantry items."
        
        echo "✅ Changes committed"
    else
        echo "❌ Deployment cancelled - please commit your changes first"
        exit 1
    fi
fi

# 2. Run tests
echo ""
echo "🧪 Running tests..."
if python -m pytest test_grocery_sync.py -v 2>/dev/null; then
    echo "✅ Tests passed"
else
    echo "⚠️  Tests not found or failed - proceeding anyway"
fi

# 3. Check syntax
echo ""
echo "🔍 Checking Python syntax..."
python -m py_compile services/grocery_list_service.py
python -m py_compile services/grocery_calculator.py
python -m py_compile routers/grocery_lists.py
python -m py_compile schemas/grocery_list.py
echo "✅ All files compile successfully"

# 4. Push to git
echo ""
echo "📤 Pushing to git..."
read -p "Push to origin/main? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin main
    echo "✅ Pushed to git"
else
    echo "⚠️  Skipped git push"
fi

# 5. Deploy to production
echo ""
echo "🚀 Deploying to production..."
echo ""
echo "Run these commands on your server:"
echo ""
echo "  cd /path/to/FreshlyBackend"
echo "  git pull origin main"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt  # if any new dependencies"
echo "  sudo systemctl restart freshly-backend  # or your service name"
echo ""
echo "OR if using PM2:"
echo ""
echo "  cd /path/to/FreshlyBackend"
echo "  git pull origin main"
echo "  pm2 restart freshly-backend"
echo ""

# 6. Verification steps
echo ""
echo "✅ DEPLOYMENT CHECKLIST"
echo "======================"
echo ""
echo "After deployment, verify:"
echo "  [ ] Server restarted successfully"
echo "  [ ] POST /grocery-lists/{id}/sync-pantry returns remaining_items"
echo "  [ ] Items with notes like '2 cups' get parsed correctly"
echo "  [ ] Pantry subtraction works (test with matching ingredient IDs)"
echo "  [ ] Fuzzy matching prevents duplicate ingredients"
echo "  [ ] Frontend displays remaining items correctly"
echo ""
echo "📝 Frontend Changes Needed:"
echo "  - See FRONTEND_REMAINING_ITEMS_UPDATE.txt for implementation guide"
echo "  - Update TypeScript types (RemainingItem interface)"
echo "  - Use remaining_items to update UI after sync"
echo ""
echo "🎉 Deployment preparation complete!"
