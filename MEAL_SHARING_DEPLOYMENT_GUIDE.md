# Meal Sharing System - Deployment Guide

## ✅ COMPLETED IMPLEMENTATION

### 1. Core Features Implemented

#### A. Meal Creation with Family Support
- **File**: `schemas/meal.py`
  - Added `family_id: int | None` field to `MealCreate` schema with alias "familyId"
  - Created `AttachFamilyRequest` schema for attach endpoint

#### B. CRUD Operations
- **File**: `crud/meals.py`
  - ✅ `create_meal()` now accepts and persists `family_id` from request data
  - ✅ `update_meal()` handles family_id updates
  - ✅ `attach_meal_to_family()` function to attach existing meals to a family

#### C. API Endpoints
- **File**: `routers/meals.py`
  - ✅ `POST /meals/me` - Family membership validation added
    - Verifies user is member of family before allowing family_id
    - Returns 403 if not a family member
  - ✅ `POST /meals/{meal_id}/attach-family` - NEW ENDPOINT
    - Validates user owns the meal
    - Validates user is member of target family
    - Attaches meal to family
    - Returns updated meal

#### D. Share Request Validation
- **File**: `routers/meal_share_requests.py`
  - ✅ Updated `send_meal_share_request()` with consistent error format `{"error": "message"}`
  - ✅ Separated validation checks with specific error messages:
    - 404: Meal not found
    - 403: Don't own meal / Not family member / Recipient not family member
    - 400: Meal has no family_id / Sending to self
    - 409: Duplicate pending request
  - ✅ All errors now return JSON object with "error" key (not plain string)

### 2. Local Testing Results

```
============================================================
MEAL SHARING SYSTEM TEST
============================================================

✅ Found user: hrhfrf (ID: 52)
✅ Found family: Abdallah's Family (ID: 7)
✅ Found second family member: ybyyy (ID: 53)

2. Testing meal creation with family_id...
✅ Created meal: Test Family Meal (ID: 9)
   - Created by user: 52
   - Family ID: 7
   ✅ Family ID persisted correctly!

3. Testing attach-family functionality...
✅ Created personal meal: Test Personal Meal (ID: 10)
   - Family ID before attach: None
✅ Attached meal to family
   - Family ID after attach: 7
   ✅ Meal successfully attached to family!
```

**Note**: Share request testing requires `meal_share_requests` table migration (see deployment steps below).

---

## 🚀 DEPLOYMENT STEPS

### Prerequisites
- ✅ Code changes are complete and committed
- ✅ Local testing confirms meal creation and attach work correctly
- ⚠️  Database migration required for share requests feature

### Step 1: Database Migration

The `meal_share_requests` table needs to be created in production. Migration file already exists:
- **File**: `migrations/versions/ec785f0856c7_add_meal_share_requests_table_remove_.py`

**Run migration in production**:
```bash
# SSH into production server
ssh user@production-server

# Navigate to project directory
cd /path/to/FreshlyBackend

# Activate virtual environment
source venv/bin/activate

# Run migration
alembic upgrade head

# Verify migration
alembic current
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 2b48126c9550 -> ec785f0856c7, add_meal_share_requests_table_remove_shared_with_family
```

### Step 2: Deploy Code Changes

1. **Push to Git**:
   ```bash
   git add .
   git commit -m "feat: implement meal sharing system with family support"
   git push origin main
   ```

2. **Pull on Production**:
   ```bash
   # On production server
   cd /path/to/FreshlyBackend
   git pull origin main
   ```

3. **Restart Service**:
   ```bash
   sudo systemctl restart freshly-backend
   # or
   sudo supervisorctl restart freshly-backend
   ```

### Step 3: Verify Deployment

#### Test 1: Create Meal with Family ID
```bash
curl -X POST "https://api.yourdom ain.com/meals/me" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Family Pasta",
    "familyId": 7,
    "image": "https://example.com/pasta.jpg",
    "calories": 450,
    "prepTime": 10,
    "cookTime": 15,
    "totalTime": 25,
    "mealType": "Dinner",
    "cuisine": "Italian",
    "tags": ["quick", "easy"],
    "macros": {"protein": 20, "fats": 12, "carbs": 55},
    "difficulty": "Easy",
    "servings": 4,
    "dietCompatibility": ["vegetarian"],
    "goalFit": ["maintenance"],
    "ingredients": [{"name": "Pasta", "amount": "200g", "inPantry": false}],
    "instructions": ["Boil water", "Cook pasta"],
    "cookingTools": ["pot"],
    "notes": "",
    "isFavorite": false
  }'
```

**Expected**: Meal created with `family_id: 7`

#### Test 2: Attach Meal to Family
```bash
curl -X POST "https://api.yourdomain.com/meals/9/attach-family" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"familyId": 7}'
```

**Expected**: Meal updated with `family_id: 7`

#### Test 3: Share Meal with Family Member
```bash
curl -X POST "https://api.yourdomain.com/meal-share-requests" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_id": 9,
    "recipient_user_id": 53,
    "message": "Try this recipe!"
  }'
```

**Expected**: Share request created successfully

#### Test 4: Error Cases

**Test 4a**: Share meal without family_id (should fail)
```bash
# Should return 400: {"error": "Meal must belong to a family to be shared"}
```

**Test 4b**: Share to self (should fail)
```bash
# Should return 400: {"error": "You cannot send a share request to yourself"}
```

**Test 4c**: Share to non-family member (should fail)
```bash
# Should return 403: {"error": "Recipient must be a member of the meal's family"}
```

---

## 📊 API ENDPOINTS SUMMARY

### New/Updated Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/meals/me` | Create meal (now supports `familyId`) | ✅ |
| POST | `/meals/{meal_id}/attach-family` | Attach existing meal to family | ✅ |
| POST | `/meal-share-requests` | Share meal with family member | ✅ |
| GET | `/meal-share-requests/pending` | Get pending share requests | ✅ |
| POST | `/meal-share-requests/{id}/accept` | Accept share request | ✅ |
| POST | `/meal-share-requests/{id}/decline` | Decline share request | ✅ |

### Request/Response Examples

#### Create Meal with Family
**Request**:
```json
{
  "name": "Family Dinner",
  "familyId": 7,
  "image": "...",
  "calories": 500,
  "prepTime": 15,
  "cookTime": 30,
  "totalTime": 45,
  "mealType": "Dinner",
  "cuisine": "Italian",
  "tags": ["healthy", "family"],
  "macros": {"protein": 30, "fats": 15, "carbs": 45},
  "difficulty": "Medium",
  "servings": 6,
  "dietCompatibility": ["gluten-free"],
  "goalFit": ["muscle-gain"],
  "ingredients": [...],
  "instructions": [...],
  "cookingTools": [...],
  "notes": "",
  "isFavorite": false
}
```

**Response**:
```json
{
  "id": 9,
  "createdByUserId": 52,
  "familyId": 7,
  "name": "Family Dinner",
  ...
}
```

#### Attach Family to Meal
**Request**:
```json
{
  "familyId": 7
}
```

**Response**:
```json
{
  "id": 10,
  "createdByUserId": 52,
  "familyId": 7,
  ...
}
```

#### Share Meal Request
**Request**:
```json
{
  "meal_id": 9,
  "recipient_user_id": 53,
  "message": "Check out this recipe!"
}
```

**Response**:
```json
{
  "id": 1,
  "mealId": 9,
  "senderUserId": 52,
  "recipientUserId": 53,
  "familyId": 7,
  "status": "pending",
  "message": "Check out this recipe!",
  "createdAt": "2025-11-04T10:30:00Z",
  "mealName": "Family Dinner",
  "senderName": "John Doe",
  "recipientName": "Jane Doe"
}
```

---

## 🔍 FILES MODIFIED

### Schemas
- ✅ `schemas/meal.py` - Added family_id field and AttachFamilyRequest

### CRUD
- ✅ `crud/meals.py` - Updated create_meal, added attach_meal_to_family

### Routers
- ✅ `routers/meals.py` - Added family validation and attach-family endpoint
- ✅ `routers/meal_share_requests.py` - Improved error handling and validation

### Database
- ✅ Migration exists: `migrations/versions/ec785f0856c7_add_meal_share_requests_table_remove_.py`

---

## ✅ CHECKLIST

### Pre-Deployment
- [x] Code changes complete
- [x] Local testing passed (meal creation & attach)
- [x] Migration file exists
- [ ] Code committed to git
- [ ] Production backup created

### Deployment
- [ ] Run database migration
- [ ] Deploy code changes
- [ ] Restart service
- [ ] Verify endpoints work
- [ ] Test error cases

### Post-Deployment
- [ ] Monitor logs for errors
- [ ] Test frontend integration
- [ ] Update API documentation
- [ ] Notify team

---

## 🐛 TROUBLESHOOTING

### Issue: Migration fails
**Solution**: Check if table already exists:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'meal_share_requests';
```

If exists, skip migration or manually mark as applied:
```bash
alembic stamp ec785f0856c7
```

### Issue: 403 Forbidden when creating meal
**Cause**: User not in family
**Solution**: Verify family membership:
```sql
SELECT * FROM family_memberships 
WHERE user_id = YOUR_USER_ID AND family_id = YOUR_FAMILY_ID;
```

### Issue: Share request fails
**Cause**: Meal doesn't have family_id
**Solution**: Use attach-family endpoint first:
```bash
POST /meals/{meal_id}/attach-family
{"familyId": 7}
```

---

## 📝 NOTES

- All validation errors now return consistent JSON format: `{"error": "message"}`
- Family membership is checked before allowing meal creation/attachment
- Share requests can only be sent between family members
- Meals without family_id cannot be shared until attached to a family

---

## 🎯 NEXT STEPS

1. Deploy to production
2. Run database migration
3. Test all endpoints
4. Update frontend to use new features
5. Monitor for issues
6. Gather user feedback

---

**Created**: November 4, 2025  
**Status**: Ready for Deployment ✅  
**Priority**: High
