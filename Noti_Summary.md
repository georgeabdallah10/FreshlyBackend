# Freshly Backend - Notification System Summary

**Document Version:** 1.0  
**Date:** December 11, 2025  
**Purpose:** Complete technical documentation of the Freshly notification system including meal sharing, family interactions, and system announcements.

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Database Schema](#database-schema)
3. [Notification Types](#notification-types)
4. [API Endpoints](#api-endpoints)
5. [Meal Share Request System](#meal-share-request-system)
6. [Family System Integration](#family-system-integration)
7. [Chat System (AI Assistant)](#chat-system-ai-assistant)
8. [Implementation Details](#implementation-details)
9. [Caching & Performance](#caching--performance)
10. [Use Cases & Workflows](#use-cases--workflows)

---

## System Overview

The Freshly notification system is a comprehensive event-driven notification platform that tracks user interactions across the application. It consists of three main subsystems:

1. **Notification Management System** - Core notification CRUD operations
2. **Meal Share Request System** - Meal sharing between users with notifications
3. **Family Interaction System** - Family member management with event notifications

### Architecture
- **Backend:** FastAPI + SQLAlchemy 2.0 + PostgreSQL
- **Authentication:** JWT-based with role-based access control
- **Caching:** Redis with in-memory fallback
- **Rate Limiting:** Tier-aware (free/pro users)

---

## Database Schema

### 1. Notifications Table (`notifications`)

**Purpose:** Central notification storage for all user notifications

```sql
CREATE TABLE notifications (
    id                      INTEGER PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                    ENUM('meal_share_request', 'meal_share_accepted', 
                                  'meal_share_declined', 'family_invite', 
                                  'family_member_joined', 'system') NOT NULL,
    title                   VARCHAR(255) NOT NULL,
    message                 TEXT NOT NULL,
    related_meal_id         INTEGER REFERENCES meals(id) ON DELETE CASCADE,
    related_user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    related_family_id       INTEGER REFERENCES families(id) ON DELETE CASCADE,
    related_share_request_id INTEGER REFERENCES meal_share_requests(id) ON DELETE CASCADE,
    is_read                 BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    read_at                 TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notif_user_read_created ON notifications(user_id, is_read, created_at);
CREATE INDEX idx_notif_user_created ON notifications(user_id, created_at);
```

**Key Fields:**
- `user_id`: Recipient of the notification
- `type`: Enum defining notification category
- `related_*_id`: Foreign keys linking to relevant entities
- `is_read`: Tracking read/unread status
- `read_at`: Timestamp when notification was marked as read

### 2. Meal Share Requests Table (`meal_share_requests`)

**Purpose:** Track meal sharing requests between users

```sql
CREATE TABLE meal_share_requests (
    id                  INTEGER PRIMARY KEY,
    meal_id             INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    sender_user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id           INTEGER REFERENCES families(id) ON DELETE CASCADE,
    accepted_meal_id    INTEGER REFERENCES meals(id) ON DELETE SET NULL,
    status              ENUM('pending', 'accepted', 'declined') NOT NULL DEFAULT 'pending',
    message             VARCHAR(500),
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    responded_at        TIMESTAMP WITH TIME ZONE
);

-- Indexes for common queries
CREATE INDEX idx_msr_recipient_status ON meal_share_requests(recipient_user_id, status);
CREATE INDEX idx_msr_family_status_created ON meal_share_requests(family_id, status, created_at);
CREATE INDEX idx_msr_sender_created ON meal_share_requests(sender_user_id, created_at);
```

**Key Fields:**
- `sender_user_id`: User sharing the meal
- `recipient_user_id`: User receiving the share request
- `meal_id`: Original meal being shared
- `accepted_meal_id`: Cloned meal created when request is accepted
- `status`: Request state (pending/accepted/declined)
- `family_id`: Optional family context for the share

### 3. Chat Tables (AI Assistant, NOT User-to-User Messaging)

**Note:** The chat system is for AI-assisted meal planning, NOT for messaging between users.

```sql
CREATE TABLE chat_conversations (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    title       VARCHAR(255),
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id              INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id),
    role            VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content         TEXT NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

## Notification Types

### 1. `meal_share_request`
**Trigger:** User A sends a meal share request to User B  
**Recipient:** User B (recipient)  
**Title:** "New Meal Share Request"  
**Message:** "{sender_name} wants to share '{meal_name}' with you"  
**Related Data:**
- `related_meal_id`: The meal being shared
- `related_user_id`: Sender's user ID
- `related_share_request_id`: The share request ID

### 2. `meal_share_accepted`
**Trigger:** User B accepts a meal share request from User A  
**Recipient:** User A (sender)  
**Title:** "Meal Share Accepted"  
**Message:** "{receiver_name} accepted your meal '{meal_name}' and now has their own copy."  
**Related Data:**
- `related_meal_id`: Original meal
- `related_user_id`: Receiver's user ID
- `related_share_request_id`: The share request ID

### 3. `meal_share_declined`
**Trigger:** User B declines a meal share request from User A  
**Recipient:** User A (sender)  
**Title:** "Meal Share Declined"  
**Message:** "{receiver_name} declined your meal '{meal_name}'"  
**Related Data:**
- `related_meal_id`: The meal
- `related_user_id`: Receiver's user ID
- `related_share_request_id`: The share request ID

### 4. `family_invite`
**Status:** Defined in schema but NOT CURRENTLY IMPLEMENTED  
**Purpose:** Would notify users when invited to a family  
**Note:** Currently families use invite codes instead of direct invitations

### 5. `family_member_joined`
**Trigger:** New member joins a family using invite code  
**Recipient:** Family owner  
**Title:** "New Family Member"  
**Message:** "{new_member_name} joined your family '{family_name}'"  
**Related Data:**
- `related_family_id`: The family
- `related_user_id`: New member's user ID

### 6. `system`
**Status:** Defined in schema but NO ENDPOINTS EXIST for creation  
**Purpose:** Developer team announcements/updates  
**Use Case:** System maintenance, new features, important updates  
**Note:** Would require admin-level endpoints to create (not yet implemented)

---

## API Endpoints

### Base URL
All notification endpoints are prefixed with `/notifications`

### Authentication
All endpoints require JWT authentication via `Authorization: Bearer {token}` header.

---

### GET `/notifications`
**Description:** Get all notifications for the current user with filtering and pagination

**Query Parameters:**
- `unreadOnly` (boolean, default: false) - Filter to only unread notifications
- `type` (string, optional) - Filter by notification type
- `skip` (integer, default: 0) - Pagination offset
- `limit` (integer, default: 50, max: 100) - Pagination limit

**Rate Limiting:** Applied via `rate_limiter_with_user("notifications")`

**Cache Control:** `max_age=30, private=true` (cached for 30 seconds)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "userId": 5,
    "type": "meal_share_request",
    "title": "New Meal Share Request",
    "message": "John Doe wants to share 'Chicken Alfredo' with you",
    "relatedMealId": 42,
    "relatedUserId": 3,
    "relatedFamilyId": null,
    "relatedShareRequestId": 12,
    "isRead": false,
    "createdAt": "2025-12-11T10:30:00Z",
    "readAt": null,
    "relatedUserName": "John Doe",
    "relatedMealName": "Chicken Alfredo",
    "relatedFamilyName": null
  }
]
```

**Example Usage:**
```bash
# Get all notifications
curl -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications

# Get only unread notifications
curl -H "Authorization: Bearer {token}" \
  "https://api.freshly.com/notifications?unreadOnly=true"

# Get only meal share requests
curl -H "Authorization: Bearer {token}" \
  "https://api.freshly.com/notifications?type=meal_share_request"
```

---

### GET `/notifications/unread-count`
**Description:** Get the count of unread notifications for the current user

**Caching:** Results cached in Redis for 30 seconds using key `notifications:unread:{user_id}`

**Rate Limiting:** Applied via `rate_limiter_with_user("notifications")`

**Response:** `200 OK`
```json
{
  "count": 5
}
```

**Example Usage:**
```bash
curl -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/unread-count
```

---

### GET `/notifications/stats`
**Description:** Get detailed notification statistics for the current user

**Response:** `200 OK`
```json
{
  "total": 23,
  "unread": 5,
  "unreadByType": {
    "meal_share_request": 2,
    "meal_share_accepted": 1,
    "family_member_joined": 2
  }
}
```

**Example Usage:**
```bash
curl -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/stats
```

---

### GET `/notifications/{notification_id}`
**Description:** Get a specific notification by ID

**Path Parameters:**
- `notification_id` (integer) - The notification ID

**Authorization:** User must own the notification (403 if not owner)

**Response:** `200 OK` - Same schema as list endpoint

**Errors:**
- `404 Not Found` - Notification doesn't exist
- `403 Forbidden` - Not authorized to view this notification

**Example Usage:**
```bash
curl -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/123
```

---

### PATCH `/notifications/{notification_id}/read`
**Description:** Mark a specific notification as read

**Path Parameters:**
- `notification_id` (integer) - The notification ID

**Side Effects:**
- Sets `is_read` to `true`
- Sets `read_at` to current timestamp
- Invalidates cache pattern `notifications:unread:{user_id}`

**Response:** `200 OK` - Returns updated notification

**Errors:**
- `404 Not Found` - Notification doesn't exist
- `403 Forbidden` - Not authorized to modify this notification

**Example Usage:**
```bash
curl -X PATCH -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/123/read
```

---

### PATCH `/notifications/{notification_id}/unread`
**Description:** Mark a specific notification as unread

**Path Parameters:**
- `notification_id` (integer) - The notification ID

**Side Effects:**
- Sets `is_read` to `false`
- Sets `read_at` to `null`
- Invalidates cache pattern `notifications:unread:{user_id}`

**Response:** `200 OK` - Returns updated notification

**Example Usage:**
```bash
curl -X PATCH -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/123/unread
```

---

### POST `/notifications/mark-all-read`
**Description:** Mark all notifications as read for the current user

**Side Effects:**
- Updates all unread notifications for the user
- Invalidates cache pattern `notifications:unread:{user_id}`

**Response:** `200 OK`
```json
{
  "message": "Marked 5 notifications as read",
  "count": 5
}
```

**Example Usage:**
```bash
curl -X POST -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/mark-all-read
```

---

### DELETE `/notifications/{notification_id}`
**Description:** Delete a specific notification

**Path Parameters:**
- `notification_id` (integer) - The notification ID

**Authorization:** User must own the notification

**Side Effects:**
- If notification was unread, invalidates cache

**Response:** `204 No Content`

**Errors:**
- `404 Not Found` - Notification doesn't exist
- `403 Forbidden` - Not authorized to delete this notification

**Example Usage:**
```bash
curl -X DELETE -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/123
```

---

### DELETE `/notifications/read/all`
**Description:** Delete all read notifications for the current user

**Response:** `200 OK`
```json
{
  "message": "Deleted 10 read notifications",
  "count": 10
}
```

**Example Usage:**
```bash
curl -X DELETE -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/read/all
```

---

### DELETE `/notifications/all`
**Description:** Delete ALL notifications (read and unread) for the current user

**Side Effects:**
- Invalidates cache pattern `notifications:unread:{user_id}`

**Response:** `200 OK`
```json
{
  "message": "Deleted 23 notifications",
  "count": 23
}
```

**Example Usage:**
```bash
curl -X DELETE -H "Authorization: Bearer {token}" \
  https://api.freshly.com/notifications/all
```

---

## Meal Share Request System

### Overview
The meal share request system allows users to share their meal recipes with other users (typically family members). When a request is accepted, the meal is **cloned** for the recipient.

### Workflow

#### 1. Send Meal Share Request

**Endpoint:** `POST /meal-share-requests`

**Request Body:**
```json
{
  "mealId": 42,
  "recipientUserId": 5,
  "message": "Try this recipe, it's amazing!"
}
```

**Business Logic:**
1. Validate sender owns the meal
2. Check sender is not sending to themselves
3. Check for existing pending requests
4. Create share request with status "pending"
5. Create notification of type `meal_share_request` for recipient
6. Return created request

**Response:** `201 Created`
```json
{
  "id": 12,
  "mealId": 42,
  "senderUserId": 3,
  "recipientUserId": 5,
  "familyId": 1,
  "status": "pending",
  "message": "Try this recipe, it's amazing!",
  "createdAt": "2025-12-11T10:30:00Z",
  "updatedAt": "2025-12-11T10:30:00Z",
  "respondedAt": null,
  "acceptedMealId": null,
  "mealName": "Chicken Alfredo",
  "senderName": "John Doe",
  "recipientName": "Jane Smith",
  "mealDetail": { /* full meal object */ },
  "acceptedMealDetail": null
}
```

**Errors:**
- `404 Not Found` - Meal doesn't exist
- `403 Forbidden` - User doesn't own the meal
- `400 Bad Request` - Trying to share with self
- `409 Conflict` - Pending request already exists

---

#### 2. View Pending Requests

**Endpoint:** `GET /meal-share-requests/pending`

**Description:** Get all pending meal share requests sent TO the current user

**Response:** `200 OK` - Array of share request objects

---

**Endpoint:** `GET /meal-share-requests/sent`

**Description:** Get all meal share requests the current user has SENT

**Response:** `200 OK` - Array of share request objects

---

**Endpoint:** `GET /meal-share-requests/received`

**Description:** Get all meal share requests the current user has RECEIVED

**Response:** `200 OK` - Array of share request objects

---

#### 3. Respond to Share Request

**Endpoint:** `POST /meal-share-requests/{request_id}/respond`

**Request Body:**
```json
{
  "action": "accept"  // or "decline"
}
```

**Business Logic (Accept):**
1. Validate recipient is the current user
2. Validate request is still pending
3. Clone the meal for the recipient:
   - Copy all meal properties (name, ingredients, instructions, etc.)
   - Set `created_by_user_id` to recipient
   - Set `family_id` to `null` (personal meal)
   - Set `is_favorite` to `false`
4. Update request:
   - Set `status` to "accepted"
   - Set `responded_at` to current timestamp
   - Set `accepted_meal_id` to cloned meal ID
5. Create notification of type `meal_share_accepted` for sender
6. Return updated request

**Business Logic (Decline):**
1. Validate recipient is the current user
2. Validate request is still pending
3. Update request:
   - Set `status` to "declined"
   - Set `responded_at` to current timestamp
4. Create notification of type `meal_share_declined` for sender
5. Return updated request

**Response:** `200 OK` - Updated share request object

**Errors:**
- `404 Not Found` - Request doesn't exist
- `403 Forbidden` - Not the recipient
- `400 Bad Request` - Request already responded to

---

#### 4. Cancel Share Request

**Endpoint:** `DELETE /meal-share-requests/{request_id}`

**Description:** Cancel a pending share request (sender only)

**Business Logic:**
1. Validate sender is the current user
2. Validate request is still pending
3. Delete the request

**Response:** `204 No Content`

**Errors:**
- `404 Not Found` - Request doesn't exist
- `403 Forbidden` - Not the sender
- `400 Bad Request` - Can only cancel pending requests

---

#### 5. View Accepted Meals

**Endpoint:** `GET /meal-share-requests/accepted-meals`

**Description:** Get all meals that the current user has accepted from others

**Response:** `200 OK` - Array of meal objects

---

### Meal Cloning Details

When a meal is accepted, the system creates a **complete clone** of the meal:

**Cloned Fields:**
- `name` - Meal name
- `image` - Image URL
- `calories` - Calorie count
- `prep_time` - Preparation time
- `cook_time` - Cooking time
- `total_time` - Total time
- `meal_type` - Type (breakfast, lunch, dinner, snack)
- `cuisine` - Cuisine type
- `tags` - Array of tags (deep copied)
- `macros` - Macro nutrients object (deep copied)
- `difficulty` - Difficulty level
- `servings` - Number of servings
- `diet_compatibility` - Diet types (deep copied)
- `goal_fit` - Fitness goals (deep copied)
- `ingredients` - Ingredients array (deep copied)
- `instructions` - Cooking instructions (deep copied)
- `cooking_tools` - Required tools (deep copied)
- `notes` - Additional notes

**Modified Fields:**
- `created_by_user_id` - Set to recipient's ID
- `family_id` - Set to `null` (personal meal)
- `is_favorite` - Set to `false`

**Not Cloned:**
- `id` - New ID generated
- `created_at` - New timestamp
- `updated_at` - New timestamp

---

## Family System Integration

### Family Structure

**Endpoint:** `GET /families`  
Get all families the current user belongs to

**Endpoint:** `POST /families`  
Create a new family (creator becomes owner)

**Request Body:**
```json
{
  "displayName": "Smith Family"
}
```

**Response:** Returns family with generated `invite_code`

---

### Joining Families

**Endpoint:** `POST /families/join`

**Request Body:**
```json
{
  "inviteCode": "ABC123XYZ"
}
```

**Business Logic:**
1. Validate invite code
2. Create membership with role "member"
3. Create notification of type `family_member_joined` for family owner

**Response:** `200 OK` - Membership object

---

### Family Members

**Endpoint:** `GET /families/{family_id}/members`

**Authorization:** Must be a family member (any role)

**Response:** Array of membership objects with user details

---

### Family Roles

The system has three roles:
- **owner** - Family creator, full permissions
- **admin** - Can manage members, cannot modify owner
- **member** - Basic access

---

### Meal Sharing Within Families

When meals are shared within a family context:
1. The `family_id` field on the share request is populated
2. Notifications include family context
3. Members can share meals with each other

---

## Chat System (AI Assistant)

**IMPORTANT:** The chat system is for AI-assisted meal planning, NOT for user-to-user messaging.

### Endpoints

**POST /chat** - Send message to AI assistant  
**GET /chat/conversations** - Get user's AI conversations  
**GET /chat/conversations/{conversation_id}** - Get conversation details  
**GET /chat/conversations/{conversation_id}/messages** - Get messages  
**DELETE /chat/conversations/{conversation_id}** - Delete conversation  
**POST /chat/image** - Generate meal images with DALL-E  
**POST /chat/scan-image** - Analyze food images

### Rate Limiting

**Free Tier:**
- 10 chat messages per minute
- 50 chat messages per day
- 2 image generations per minute
- 10 image generations per day

**Pro Tier:**
- 30 chat messages per minute
- 200 chat messages per day
- 5 image generations per minute
- 50 image generations per day

---

## Implementation Details

### CRUD Operations

**File:** `crud/notifications.py`

**Key Functions:**

1. **create_notification(db, data: NotificationCreate)** → Notification
   - Creates a new notification
   - Sets `is_read` to `false`

2. **get_notification(db, notification_id)** → Optional[Notification]
   - Retrieves single notification by ID

3. **get_user_notifications(db, user_id, unread_only, notification_type, skip, limit)** → List[Notification]
   - Query with filters and pagination
   - Ordered by `created_at` DESC

4. **get_unread_count(db, user_id)** → int
   - Count of unread notifications

5. **get_notification_stats(db, user_id)** → Dict
   - Total count, unread count, unread by type

6. **mark_as_read(db, notification)** → Notification
   - Sets `is_read` = true, `read_at` = now

7. **mark_as_unread(db, notification)** → Notification
   - Sets `is_read` = false, `read_at` = null

8. **mark_all_as_read(db, user_id)** → int
   - Bulk update, returns count

9. **delete_notification(db, notification)** → None
   - Delete single notification

10. **delete_all_read_notifications(db, user_id)** → int
    - Bulk delete read notifications

11. **delete_all_notifications(db, user_id)** → int
    - Bulk delete all notifications

**Helper Functions for Specific Notification Types:**

- **create_meal_share_request_notification(db, receiver_id, sender_name, meal_name, share_request_id, meal_id, sender_id)**

- **create_meal_share_accepted_notification(db, sender_id, receiver_name, meal_name, share_request_id, meal_id, receiver_id)**

- **create_meal_share_declined_notification(db, sender_id, receiver_name, meal_name, share_request_id, meal_id, receiver_id)**

- **create_family_member_joined_notification(db, family_owner_id, new_member_name, family_name, family_id, new_member_id)**

---

### Meal Share Request CRUD

**File:** `crud/meal_share_requests.py`

**Key Functions:**

1. **create_share_request(db, data, sender_user_id, meal)** → MealShareRequest
   - Creates pending request

2. **get_share_request(db, request_id)** → Optional[MealShareRequest]
   - Retrieves single request

3. **get_pending_requests_for_user(db, user_id)** → List[MealShareRequest]
   - Requests where user is recipient and status is pending

4. **get_sent_requests(db, sender_user_id)** → List[MealShareRequest]
   - All requests sent by user

5. **get_received_requests(db, recipient_user_id)** → List[MealShareRequest]
   - All requests received by user

6. **accept_share_request(db, request)** → Tuple[MealShareRequest, Meal]
   - Clones meal
   - Updates request status to "accepted"
   - Sets `responded_at` and `accepted_meal_id`
   - Returns updated request and cloned meal

7. **decline_share_request(db, request)** → MealShareRequest
   - Updates status to "declined"
   - Sets `responded_at`

8. **check_existing_request(db, meal_id, sender_user_id, recipient_user_id)** → Optional[MealShareRequest]
   - Check for duplicate pending requests

9. **delete_share_request(db, request)** → None
   - Delete/cancel request

10. **_clone_meal_for_user(db, meal, recipient_user_id)** → Meal
    - Internal: creates meal clone with deep copy of arrays/objects

---

## Caching & Performance

### Redis Caching

**Key:** `notifications:unread:{user_id}`  
**TTL:** 30 seconds  
**Usage:** Unread count endpoint

**Invalidation:**
- When notification marked as read/unread
- When unread notification deleted
- When all notifications deleted
- Pattern: `await invalidate_cache_pattern(f"notifications:unread:{user_id}")`

### In-Memory Fallback

If Redis is unavailable, the system uses `InMemoryCache` with TTL support.

### Database Indexes

**Notifications:**
- `idx_notifications_user_id` - User lookup
- `idx_notifications_is_read` - Read status filtering
- `idx_notif_user_read_created` - Composite for common query pattern
- `idx_notif_user_created` - User + created timestamp

**Meal Share Requests:**
- `idx_msr_recipient_status` - Recipient pending requests
- `idx_msr_family_status_created` - Family context queries
- `idx_msr_sender_created` - Sender history

### Cache Control Headers

**Endpoint:** `GET /notifications`  
**Header:** `Cache-Control: private, max-age=30`  
**Behavior:** Client can cache for 30 seconds

---

## Use Cases & Workflows

### Use Case 1: User Shares a Meal

**Actors:** User A (sender), User B (recipient)

**Steps:**
1. User A selects their meal "Chicken Alfredo"
2. User A clicks "Share" and selects User B from family members
3. User A optionally adds a message
4. User A confirms share

**Backend Flow:**
1. POST `/meal-share-requests`
2. System validates User A owns the meal
3. System creates `MealShareRequest` with status "pending"
4. System creates notification for User B:
   - Type: `meal_share_request`
   - Title: "New Meal Share Request"
   - Message: "User A wants to share 'Chicken Alfredo' with you"
5. User B receives notification

**Frontend Updates:**
- User B's notification badge increments
- Notification appears in User B's notification center
- User B can navigate to share request details

---

### Use Case 2: User Accepts a Meal Share

**Actors:** User B (recipient), User A (sender)

**Steps:**
1. User B opens notification
2. User B views meal details
3. User B clicks "Accept"

**Backend Flow:**
1. POST `/meal-share-requests/{request_id}/respond` with `action: "accept"`
2. System validates User B is recipient
3. System clones meal:
   - Copies all meal data
   - Sets new owner to User B
   - Creates new meal record
4. System updates share request:
   - Status: "accepted"
   - Sets `responded_at`
   - Sets `accepted_meal_id` to cloned meal
5. System creates notification for User A:
   - Type: `meal_share_accepted`
   - Title: "Meal Share Accepted"
   - Message: "User B accepted your meal 'Chicken Alfredo' and now has their own copy."

**Frontend Updates:**
- User B now has meal in their meal list
- User B's notification marked as read (optional)
- User A receives acceptance notification
- Share request marked as accepted in both users' views

---

### Use Case 3: User Declines a Meal Share

**Actors:** User B (recipient), User A (sender)

**Steps:**
1. User B opens notification
2. User B clicks "Decline"

**Backend Flow:**
1. POST `/meal-share-requests/{request_id}/respond` with `action: "decline"`
2. System validates User B is recipient
3. System updates share request:
   - Status: "declined"
   - Sets `responded_at`
4. System creates notification for User A:
   - Type: `meal_share_declined`
   - Title: "Meal Share Declined"
   - Message: "User B declined your meal 'Chicken Alfredo'"

---

### Use Case 4: New Family Member Joins

**Actors:** New User (joiner), Family Owner

**Steps:**
1. New User receives invite code from family member
2. New User enters invite code
3. New User clicks "Join Family"

**Backend Flow:**
1. POST `/families/join` with `inviteCode`
2. System validates invite code
3. System creates `FamilyMembership` with role "member"
4. System creates notification for family owner:
   - Type: `family_member_joined`
   - Title: "New Family Member"
   - Message: "New User joined your family 'Smith Family'"

---

### Use Case 5: User Checks Notifications

**Actors:** User

**Steps:**
1. User opens app
2. App requests unread count
3. User opens notification center
4. User views notifications
5. User marks notification as read
6. User deletes old notifications

**Backend Flow:**
1. GET `/notifications/unread-count` - Cache hit/miss logic
2. GET `/notifications?unreadOnly=true`
3. User taps notification
4. PATCH `/notifications/{id}/read`
5. DELETE `/notifications/{id}` or DELETE `/notifications/read/all`

---

### Use Case 6: System Announcement (Future)

**Note:** Not currently implemented - requires admin endpoints

**Proposed Flow:**
1. Admin creates system notification via admin panel
2. POST `/admin/notifications/broadcast` (not implemented)
3. System creates notification for all users or filtered subset:
   - Type: `system`
   - Title: "New Feature Available"
   - Message: "Check out our new meal planning wizard!"
4. All users receive notification

**Implementation Required:**
- Admin authentication/authorization
- Broadcast endpoint
- Optional: User preferences for system notifications
- Optional: Notification scheduling

---

## Missing Features & Future Enhancements

### 1. System Notifications
**Status:** Schema defined, no implementation  
**Requirements:**
- Admin authentication system
- Broadcast endpoint: `POST /admin/notifications/broadcast`
- Target filtering (all users, specific tier, specific families)
- Scheduling capabilities
- User preferences for system notifications

### 2. Family Invite Notifications
**Status:** Type defined, not used  
**Current:** Families use invite codes (pull model)  
**Alternative:** Direct invitations (push model)
- Send invite to specific user
- User receives notification
- User can accept/decline
- Similar to meal share request flow

### 3. Real-time Notifications
**Status:** Not implemented  
**Enhancement:** WebSocket support for live notification delivery
- WebSocket endpoint: `/ws/notifications`
- Push notifications on create
- Auto-update unread counts
- Live notification list updates

### 4. Email Notifications
**Status:** Not implemented  
**Enhancement:** Email digest for important notifications
- Daily/weekly summary emails
- Configurable per notification type
- Unsubscribe management

### 5. Push Notifications (Mobile)
**Status:** Not implemented  
**Enhancement:** Mobile push notification support
- Firebase Cloud Messaging integration
- APNs integration
- Device token registration
- Notification preferences by type

### 6. Notification Preferences
**Status:** Not implemented  
**Enhancement:** Per-user notification settings
- Enable/disable by type
- Email vs in-app preferences
- Quiet hours
- Frequency limits

### 7. Notification Actions
**Status:** Not implemented  
**Enhancement:** Quick actions from notifications
- Accept/decline share requests directly from notification
- Archive/snooze capabilities
- Bulk actions

### 8. Notification History
**Status:** Basic implementation  
**Enhancement:** Enhanced history features
- Archive instead of delete
- Search notifications
- Filter by date range
- Export notification history

---

## Error Handling

### Common HTTP Status Codes

- **200 OK** - Successful request
- **201 Created** - Resource created successfully
- **204 No Content** - Successful deletion
- **400 Bad Request** - Invalid input/validation error
- **401 Unauthorized** - Missing or invalid JWT token
- **403 Forbidden** - Authenticated but not authorized for resource
- **404 Not Found** - Resource doesn't exist
- **409 Conflict** - Resource conflict (e.g., duplicate request)
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

### Error Response Format

```json
{
  "error": "Detailed error message",
  "correlation_id": "abc123def",
  "status_code": 400
}
```

### Rate Limiting

**Notifications Endpoint:**
- Configured in `RATE_LIMIT_POLICIES`
- Uses tier-aware limiting (free/pro)
- Both burst (per minute) and daily quotas
- Returns 429 when exceeded

---

## Database Migrations

**Initial Migration:** `d8a355dfb48b_final_notifications_meal_share_tables.py`

**Creates:**
- `notifications` table with enum type `notification_type`
- `meal_share_requests` table with enum type `meal_share_request_status`
- Indexes for performance
- Foreign key relationships

**Apply Migration:**
```bash
alembic upgrade head
```

**Rollback:**
```bash
alembic downgrade -1
```

---

## Security Considerations

### 1. Authorization
- All endpoints require JWT authentication
- Users can only access their own notifications
- Users can only respond to share requests where they are recipient
- Users can only send share requests for meals they own
- Family member validation for family-related operations

### 2. Input Validation
- Pydantic schemas validate all inputs
- Enum validation for notification types
- SQL injection protection via SQLAlchemy ORM
- Rate limiting prevents abuse

### 3. Data Privacy
- Users cannot see other users' notifications
- Meal share requires explicit request/acceptance
- Family membership required for family meal access
- Cache keys include user ID to prevent cross-user cache leaks

### 4. XSS Prevention
- All user-generated content (messages, names) should be sanitized by frontend
- API returns JSON, not HTML
- CORS properly configured

---

## Testing

### Manual Testing Scripts

**File:** `test_meal_sharing.py`  
Tests meal sharing system end-to-end

**File:** `test_share_request_fix.py`  
Regression test for 500 errors

### Test Scenarios

1. **Create Notification**
   - Valid notification creation
   - Missing required fields
   - Invalid user ID

2. **Meal Share Request**
   - Send valid request
   - Duplicate request prevention
   - Self-sharing prevention
   - Non-owner sharing prevention

3. **Accept/Decline Request**
   - Valid acceptance
   - Valid decline
   - Non-recipient response attempt
   - Already responded request

4. **Notification Read Status**
   - Mark as read
   - Mark as unread
   - Mark all as read
   - Count accuracy

5. **Cache Invalidation**
   - Unread count cache
   - Invalidation on read
   - Invalidation on delete

---

## Performance Metrics

### Database Query Optimization
- Composite indexes for common query patterns
- Eager loading with `lazy="selectin"` for relationships
- Pagination to limit result sets
- Bulk operations for mark-all-read and delete-all

### Caching Strategy
- 30-second TTL for unread counts (high-read, low-consistency-critical)
- Cache invalidation on writes
- In-memory fallback for Redis unavailability

### Expected Load
- **Read-heavy:** Users check notifications frequently
- **Write spikes:** Notification creation on events
- **Bulk operations:** Infrequent but database-intensive

---

## Monitoring & Logging

### Log Levels
- **INFO:** Request/response logging
- **WARNING:** HTTP errors (4xx)
- **ERROR:** Server errors (5xx), database errors
- **DEBUG:** Cache hits/misses, detailed flow

### Correlation IDs
All requests include correlation ID in headers for tracing:
- Request: `X-Correlation-ID`
- Logs include correlation ID

### Key Metrics to Monitor
- Unread notification count per user
- Notification creation rate
- Cache hit ratio
- Database query performance
- Rate limit hits

---

## API Summary Table

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/notifications` | GET | Required | List notifications with filters |
| `/notifications/unread-count` | GET | Required | Get unread count |
| `/notifications/stats` | GET | Required | Get notification statistics |
| `/notifications/{id}` | GET | Required | Get single notification |
| `/notifications/{id}/read` | PATCH | Required | Mark as read |
| `/notifications/{id}/unread` | PATCH | Required | Mark as unread |
| `/notifications/mark-all-read` | POST | Required | Mark all as read |
| `/notifications/{id}` | DELETE | Required | Delete notification |
| `/notifications/read/all` | DELETE | Required | Delete all read |
| `/notifications/all` | DELETE | Required | Delete all notifications |
| `/meal-share-requests` | POST | Required | Send share request |
| `/meal-share-requests/pending` | GET | Required | Get pending received requests |
| `/meal-share-requests/sent` | GET | Required | Get sent requests |
| `/meal-share-requests/received` | GET | Required | Get all received requests |
| `/meal-share-requests/{id}/respond` | POST | Required | Accept/decline request |
| `/meal-share-requests/{id}` | DELETE | Required | Cancel request |
| `/meal-share-requests/accepted-meals` | GET | Required | Get accepted meals |

---

## Conclusion

The Freshly notification system is a robust, event-driven platform that handles meal sharing, family interactions, and system announcements. It provides:

- **Comprehensive notification management** with CRUD operations
- **Meal sharing workflow** with request/accept/decline flow
- **Family integration** with member join notifications
- **Performance optimization** via caching and indexes
- **Extensibility** for future enhancements like real-time push notifications

The system is production-ready with proper error handling, rate limiting, authorization, and monitoring capabilities. Future enhancements can build on this foundation to add real-time features, email notifications, and advanced notification preferences.

---

**Document End**
