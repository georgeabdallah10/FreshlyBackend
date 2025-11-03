# Notification System - Complete Implementation

## Overview
Complete notification system for user notifications including meal share requests, acceptances, declines, family events, and system notifications.

## New Files Created

### 1. Model: `models/notification.py`
- Stores all user notifications
- Links to related entities (meals, users, families, share requests)
- Tracks read/unread status
- Timestamps for created_at and read_at

### 2. Schemas: `schemas/notification.py`
- NotificationCreate - For creating notifications
- NotificationOut - For API responses with related data
- NotificationUpdate - For updating read status
- NotificationStats - For statistics

### 3. CRUD: `crud/notifications.py`
- create_notification() - Create any notification
- get_notification() - Get single notification
- get_user_notifications() - Get all with filters
- get_unread_count() - Count unread
- get_notification_stats() - Get statistics
- mark_as_read() - Mark single as read
- mark_as_unread() - Mark single as unread
- mark_all_as_read() - Mark all as read
- delete_notification() - Delete single
- delete_all_read_notifications() - Delete all read
- delete_all_notifications() - Delete all
- Helper functions for creating specific notification types

### 4. Router: `routers/notifications.py`
Complete REST API for notifications

## API Endpoints

### GET /notifications
Get all notifications for current user
- Query params: unreadOnly, type, skip, limit
- Returns array of notifications with related data

### GET /notifications/unread-count
Get count of unread notifications
- Returns: {count: number}

### GET /notifications/stats
Get notification statistics
- Returns: total, unread, unreadByType

### GET /notifications/{id}
Get specific notification by ID
- Returns single notification with full details

### PATCH /notifications/{id}/read
Mark notification as read
- Returns updated notification

### PATCH /notifications/{id}/unread
Mark notification as unread
- Returns updated notification

### POST /notifications/mark-all-read
Mark all notifications as read
- Returns count of marked notifications

### DELETE /notifications/{id}
Delete single notification
- Returns 204 No Content

### DELETE /notifications/read/all
Delete all read notifications
- Returns count of deleted notifications

### DELETE /notifications/all
Delete all notifications
- Returns count of deleted notifications

## Notification Types

1. **meal_share_request** - When someone sends you a meal share request
2. **meal_share_accepted** - When someone accepts your meal share request
3. **meal_share_declined** - When someone declines your meal share request
4. **family_invite** - When invited to join a family
5. **family_member_joined** - When someone joins your family
6. **system** - System notifications

## Automatic Notification Creation

Notifications are automatically created when:
- Someone sends you a meal share request
- Someone accepts your meal share request
- Someone declines your meal share request

## Database Changes

New table: `notifications`
Columns:
- id (PRIMARY KEY)
- user_id (FK to users)
- type (ENUM)
- title (VARCHAR 255)
- message (TEXT)
- related_meal_id (FK to meals, nullable)
- related_user_id (FK to users, nullable)
- related_family_id (FK to families, nullable)
- related_share_request_id (FK to meal_share_requests, nullable)
- is_read (BOOLEAN, default FALSE)
- created_at (TIMESTAMP)
- read_at (TIMESTAMP, nullable)

Indexes:
- user_id
- is_read

## Frontend Integration

All endpoints require Authorization Bearer token.

Example usage:
```
GET /notifications?unreadOnly=true&limit=20
GET /notifications/unread-count
GET /notifications/stats
PATCH /notifications/123/read
POST /notifications/mark-all-read
DELETE /notifications/123
```

Response format:
```json
{
  "id": 1,
  "userId": 5,
  "type": "meal_share_request",
  "title": "New Meal Share Request",
  "message": "John wants to share 'Pasta' with you",
  "relatedMealId": 10,
  "relatedUserId": 3,
  "relatedShareRequestId": 7,
  "isRead": false,
  "createdAt": "2025-11-02T10:00:00Z",
  "readAt": null,
  "relatedUserName": "John Doe",
  "relatedMealName": "Pasta Carbonara",
  "relatedFamilyName": null
}
```

## Migration Required

Run on production:
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    related_meal_id INTEGER REFERENCES meals(id) ON DELETE CASCADE,
    related_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    related_family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    related_share_request_id INTEGER REFERENCES meal_share_requests(id) ON DELETE CASCADE,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    read_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT notifications_type_check CHECK (type IN (
        'meal_share_request', 
        'meal_share_accepted', 
        'meal_share_declined', 
        'family_invite', 
        'family_member_joined', 
        'system'
    ))
);

CREATE INDEX ix_notifications_user_id ON notifications(user_id);
CREATE INDEX ix_notifications_is_read ON notifications(is_read);
```
