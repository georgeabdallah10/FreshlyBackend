# PRODUCTION COMMANDS - Fix Alembic & Deploy

## 🚨 PROBLEM SOLVED
Empty migration file `d36abaa2f689_add_shared_with_family_to_meals.py` was breaking Alembic.
**Status**: ✅ Deleted locally and pushed to git

---

## 📋 RUN THESE COMMANDS ON PRODUCTION

**Already SSH'd into production? Run these:**

```bash
# 1. Navigate to project
cd /root/FreshlyBackend

# 2. Remove empty file (if it still exists)
rm -f migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py

# 3. Pull latest code (gets the fix)
git pull origin main

# 4. Activate virtual environment
source .venv/bin/activate

# 5. Test Alembic (should work now)
alembic current

# 6. Run ALL pending migrations (including meal_share_requests table!)
alembic upgrade head

# 7. Verify migration status
alembic current

# 8. Restart service
systemctl restart freshly-backend

# 9. Check service status
systemctl status freshly-backend

# 10. Watch logs for any errors
journalctl -u freshly-backend -f
```

---

## ✅ EXPECTED OUTPUT

### Step 5 & 7 - `alembic current`
Should show current migration without errors:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
ec785f0856c7 (head)
```

### Step 6 - `alembic upgrade head`
Should create meal_share_requests table:
```
INFO  [alembic.runtime.migration] Running upgrade 2b48126c9550 -> ec785f0856c7, add_meal_share_requests_table_remove_shared_with_family
```

### Step 8 - Service restart
Should show:
```
● freshly-backend.service - Freshly Backend API
   Active: active (running)
```

---

## 🧪 TEST AFTER DEPLOYMENT

```bash
# Test the meal share request endpoint
curl -X POST "https://freshlybackend.duckdns.org/meal-share-requests" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mealId": 13, "recipientUserId": 52, "message": "Test"}'
```

**Expected**: `201 Created` ✅ (NOT 500!)

---

## 🎯 WHAT THIS FIXES

1. ✅ Alembic error: "Could not determine revision id"
2. ✅ Creates meal_share_requests table in database
3. ✅ Fixes 500 error in POST /meal-share-requests
4. ✅ Enables full meal sharing system

---

## 📞 IF SOMETHING GOES WRONG

### Error: "Relation meal_share_requests already exists"
**Meaning**: Table was already created (good!)
**Action**: Just restart service and test

### Error: "Conflict with existing migration"
**Action**: Run `alembic stamp head` then restart

### Service won't start
**Action**: Check logs with `journalctl -u freshly-backend -n 50`

---

## 🚀 QUICK COPY-PASTE

```bash
cd /root/FreshlyBackend && \
rm -f migrations/versions/d36abaa2f689_add_shared_with_family_to_meals.py && \
git pull origin main && \
source .venv/bin/activate && \
alembic upgrade head && \
systemctl restart freshly-backend && \
systemctl status freshly-backend
```

---

**Ready? Copy the commands above and paste into your SSH session!** 🚀
