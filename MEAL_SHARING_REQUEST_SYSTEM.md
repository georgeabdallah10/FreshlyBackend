# Meal Sharing System - Request-Based Implementation

## ✅ COMPLETED CHANGES

I've completely refactored the meal sharing system from Option 1 (instant family sharing) to Option 2 (request-based sharing with user approval).

---

## NEW DATABASE STRUCTURE

### Created New Table: `meal_share_requests`
Tracks all meal share requests between family members with these fields:
- id
- meal_id (which meal is being shared)
- sender_user_id (who is sending the meal)
- recipient_user_id (who is receiving the request)
- family_id (which family this is in)
- status (pending, accepted, or declined)
- message (optional note from sender)
- created_at, updated_at, responded_at (timestamps)

### Removed from `meals` table:
- shared_with_family column (no longer needed)

---

## NEW API ENDPOINTS

### 1. Send Meal Share Request
**POST** `/meal-share-requests`

Body:
```json
{
  "mealId": 123,
  "recipientUserId": 45,
  "message": "Try this recipe!"
}
```

Sends a meal to a specific family member. They will get a request notification.

---

### 2. Get Pending Requests (Inbox)
**GET** `/meal-share-requests/pending`

Returns all pending requests sent TO me (my inbox).

---

### 3. Get Sent Requests
**GET** `/meal-share-requests/sent`

Returns all requests I've sent to others.

---

### 4. Get Received Requests
**GET** `/meal-share-requests/received`

Returns all requests I've received (pending, accepted, declined).

---

### 5. Accept or Decline Request
**POST** `/meal-share-requests/{request_id}/respond`

Body:
```json
{
  "action": "accept"
}
```

or

```json
{
  "action": "decline"
}
```

Respond to a meal share request.

---

### 6. Cancel Request
**DELETE** `/meal-share-requests/{request_id}`

Cancel a pending request (only sender can do this).

---

### 7. Get My Accepted Meals
**GET** `/meal-share-requests/accepted-meals`

Get all meals I've accepted from others (my shared meal collection).

---

## REMOVED ENDPOINTS

These endpoints NO LONGER EXIST:
- ~~POST /meals/me/{meal_id}/share~~ (removed)
- ~~DELETE /meals/me/{meal_id}/share~~ (removed)
- ~~GET /meals/family/{family_id}/shared~~ (removed)

---

## HOW IT WORKS NOW

### User Flow:

1. **User A creates a meal**
   - Meal is private by default

2. **User A wants to share with User B**
   - User A clicks "Share Meal"
   - User A selects User B from family members list
   - Optionally adds a message
   - Sends request via `POST /meal-share-requests`

3. **User B receives notification**
   - User B sees pending request in `GET /meal-share-requests/pending`
   - Shows meal details, sender name, message

4. **User B responds**
   - User B can accept or decline via `POST /meal-share-requests/{id}/respond`
   - If accepted: meal appears in User B's accepted meals collection
   - If declined: request is marked as declined

5. **User B can view accepted meals**
   - `GET /meal-share-requests/accepted-meals` shows all meals they've accepted
   - These are read-only (User B can't edit User A's meal)
   - User B can use the meal as inspiration or cook it

---

## PERMISSION RULES

- ✅ Only meal owner can send share requests for their meal
- ✅ Can only send to family members in the same family
- ✅ Cannot send meal to yourself
- ✅ Only recipient can accept/decline request
- ✅ Only sender can cancel pending request
- ✅ Cannot respond to already-responded requests
- ✅ Accepted meals are read-only for recipient

---

## FILES CHANGED/CREATED

### New Files:
- `models/meal_share_request.py` - Database model
- `schemas/meal_share_request.py` - API schemas
- `crud/meal_share_requests.py` - Database operations
- `routers/meal_share_requests.py` - API endpoints
- `migrations/versions/ec785f0856c7_*.py` - Migration file

### Modified Files:
- `models/meal.py` - Removed shared_with_family column
- `schemas/meal.py` - Removed shared_with_family field
- `crud/meals.py` - Removed old sharing functions
- `routers/meals.py` - Removed old sharing endpoints
- `main.py` - Added new router

---

## DEPLOYMENT COMMANDS

### On Production Server:

```bash
# 1. SSH into server
ssh root@freshlybackend.duckdns.org

# 2. Navigate to project
cd ~/FreshlyBackend

# 3. Stop service
sudo systemctl stop freshly.service

# 4. Pull latest code
git fetch origin
git reset --hard origin/main

# 5. Activate venv
source .venv/bin/activate

# 6. Update dependencies
pip install -r requirements.txt

# 7. Run migration
# First, manually drop old column and stamp to bypass broken migrations
psql $DATABASE_URL -c "ALTER TABLE meals DROP COLUMN IF EXISTS shared_with_family;"
alembic stamp ec785f0856c7

# Now run the new migration
alembic upgrade head

# 8. Restart service
sudo systemctl restart freshly.service

# 9. Check status
sudo systemctl status freshly.service

# 10. Test endpoints
curl http://localhost:8000/health
```

---

## FRONTEND CHANGES NEEDED

Your frontend team needs to:

1. **Remove old sharing UI:**
   - Remove "Share with Family" toggle from meals
   - Remove "Family Shared Meals" feed

2. **Add new request-based UI:**
   - Add "Send to..." button on meals
   - Show family members list to select recipient
   - Add optional message field
   - Show sent requests tab (pending, accepted, declined)
   - Show inbox/notifications for pending requests
   - Add accept/decline buttons in notifications
   - Add "Shared with Me" section showing accepted meals

3. **Update API calls:**
   - Replace old sharing endpoints with new request endpoints
   - Handle request status (pending/accepted/declined)
   - Show appropriate UI based on status

---

## TESTING

Test these scenarios:

1. ✅ User can send meal request to family member
2. ✅ User cannot send to non-family member
3. ✅ User cannot send to themselves
4. ✅ Recipient can accept request
5. ✅ Recipient can decline request
6. ✅ Sender can cancel pending request
7. ✅ Cannot respond to already-responded request
8. ✅ Accepted meals appear in recipient's collection
9. ✅ Declined requests don't show meals

---

## NEXT STEPS

1. Deploy to production using commands above
2. Share this doc with frontend team
3. Test all endpoints manually
4. Update frontend to use new request-based system
5. Add push notifications for new requests (future enhancement)

---

The system is now ready for deployment! 🚀
