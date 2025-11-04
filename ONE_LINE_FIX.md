# ONE-LINE FIX 🚀

**Copy and paste this into your production SSH session:**

```bash
cd /root/FreshlyBackend && rm -f migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py && git pull origin main && source .venv/bin/activate && alembic upgrade head && systemctl restart freshly-backend && echo "✅ DONE! Test the API now."
```

**That's it!** This will:
1. ✅ Remove the empty migration file
2. ✅ Pull the fix from git  
3. ✅ Run all migrations (creates meal_share_requests table)
4. ✅ Restart the service

**Then test:**
```bash
curl -X POST "https://freshlybackend.duckdns.org/meal-share-requests" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mealId": 13, "recipientUserId": 52}'
```

**Expected**: 201 Created ✅ (not 500!)

---

**Need more details?** See `PRODUCTION_COMMANDS.md`
