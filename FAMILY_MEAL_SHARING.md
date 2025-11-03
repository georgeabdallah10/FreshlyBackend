# Family Meal Sharing Feature

## Overview
The Family Meal Sharing feature allows family members to voluntarily share their meals with other family members, while family owners get read-only access to view all member meals, preferences, and profile settings.

## Key Features

### 1. **Voluntary Meal Sharing** (All Members)
- Members can choose to share specific meals with their family
- Shared meals are visible to all family members (read-only)
- Members maintain full control over their own meals
- Only the meal creator can share/unshare their meals

### 2. **Family Owner Dashboard** (Owners Only)
- Read-only access to all member meals (shared or not)
- Read-only access to member preferences
- Read-only access to member profile information
- Permission-based access control

## Database Changes

### Meals Table
Added `shared_with_family` column:
- **Type**: Boolean
- **Default**: False
- **Nullable**: False
- **Purpose**: Tracks whether a meal is shared with the family

### Migration
- **File**: `migrations/versions/d4308a0840bd_add_shared_with_family_to_meals.py`
- **Command**: `alembic upgrade head`

## API Endpoints

### Member Endpoints (All Members)

#### 1. Share Meal with Family
```http
POST /meals/me/{meal_id}/share
```

**Description**: Share a meal with your family (voluntary)

**Authorization**: Bearer token required

**Path Parameters**:
- `meal_id` (integer): ID of the meal to share

**Success Response** (200 OK):
```json
{
  "id": 123,
  "name": "Grilled Chicken Salad",
  "sharedWithFamily": true,
  "createdByUserId": 456,
  ...
}
```

**Error Responses**:
- `404 Not Found`: Meal not found or unauthorized
- `400 Bad Request`: Meal must belong to a family / Already shared
- `401 Unauthorized`: Invalid or missing token

---

#### 2. Unshare Meal from Family
```http
DELETE /meals/me/{meal_id}/share
```

**Description**: Unshare a meal from your family

**Authorization**: Bearer token required

**Path Parameters**:
- `meal_id` (integer): ID of the meal to unshare

**Success Response** (200 OK):
```json
{
  "id": 123,
  "name": "Grilled Chicken Salad",
  "sharedWithFamily": false,
  "createdByUserId": 456,
  ...
}
```

**Error Responses**:
- `404 Not Found`: Meal not found or unauthorized
- `400 Bad Request`: Meal is not currently shared
- `401 Unauthorized`: Invalid or missing token

---

#### 3. Get Family Shared Meals
```http
GET /meals/family/{family_id}/shared
```

**Description**: View all meals shared within a family

**Authorization**: Bearer token required (must be family member)

**Path Parameters**:
- `family_id` (integer): ID of the family

**Success Response** (200 OK):
```json
[
  {
    "id": 123,
    "name": "Grilled Chicken Salad",
    "sharedWithFamily": true,
    "createdByUserId": 456,
    "calories": 450,
    "mealType": "Lunch",
    ...
  },
  {
    "id": 124,
    "name": "Pasta Primavera",
    "sharedWithFamily": true,
    "createdByUserId": 789,
    ...
  }
]
```

**Error Responses**:
- `403 Forbidden`: You are not a member of this family
- `401 Unauthorized`: Invalid or missing token

---

### Family Owner Endpoints (Owners Only)

#### 4. Get Member's All Meals
```http
GET /families/{family_id}/members/{user_id}/meals
```

**Description**: View all meals created by a family member (read-only)

**Authorization**: Bearer token required (must be family owner)

**Path Parameters**:
- `family_id` (integer): ID of the family
- `user_id` (integer): ID of the family member

**Success Response** (200 OK):
```json
[
  {
    "id": 123,
    "name": "Grilled Chicken Salad",
    "sharedWithFamily": true,
    "createdByUserId": 456,
    ...
  },
  {
    "id": 125,
    "name": "Personal Smoothie Bowl",
    "sharedWithFamily": false,
    "createdByUserId": 456,
    ...
  }
]
```

**Error Responses**:
- `403 Forbidden`: Only family owners can access this endpoint
- `404 Not Found`: User is not a member of this family
- `401 Unauthorized`: Invalid or missing token

---

#### 5. Get Member's Preferences
```http
GET /families/{family_id}/members/{user_id}/preferences
```

**Description**: View a family member's dietary preferences (read-only)

**Authorization**: Bearer token required (must be family owner)

**Path Parameters**:
- `family_id` (integer): ID of the family
- `user_id` (integer): ID of the family member

**Success Response** (200 OK):
```json
{
  "id": 78,
  "user_id": 456,
  "diet_codes": ["vegan", "gluten_free"],
  "allergen_ingredient_ids": [12, 45, 67],
  "disliked_ingredient_ids": [89, 90],
  "goal": "weight_loss",
  "calorie_target": 1800,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-11-02T15:45:00Z"
}
```

**Error Responses**:
- `403 Forbidden`: Only family owners can access this endpoint
- `404 Not Found`: User preferences not found or user is not a member
- `401 Unauthorized`: Invalid or missing token

---

#### 6. Get Member's Profile
```http
GET /families/{family_id}/members/{user_id}/profile
```

**Description**: View a family member's profile information (read-only)

**Authorization**: Bearer token required (must be family owner)

**Path Parameters**:
- `family_id` (integer): ID of the family
- `user_id` (integer): ID of the family member

**Success Response** (200 OK):
```json
{
  "id": 456,
  "name": "John Doe",
  "email": "john@example.com",
  "phone_number": "+1234567890",
  "location": "New York, NY",
  "status": "active",
  "avatar_path": "avatars/456.jpg",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-11-02T15:45:00Z"
}
```

**Error Responses**:
- `403 Forbidden`: Only family owners can access this endpoint
- `404 Not Found`: User not found or not a member of this family
- `401 Unauthorized`: Invalid or missing token

---

## Permission Model

### Family Roles
1. **Owner** (highest privileges)
   - All admin privileges
   - View all member meals (shared or not)
   - View all member preferences
   - View all member profiles
   - Delete family
   - Cannot be removed from family

2. **Admin** (moderate privileges)
   - View family shared meals
   - Manage members (add/remove)
   - Regenerate invite codes
   - Cannot access owner-only endpoints

3. **Member** (basic privileges)
   - View family shared meals
   - Share/unshare own meals
   - Manage own profile and preferences

### Access Control Matrix

| Action | Member | Admin | Owner |
|--------|--------|-------|-------|
| Share own meal | ✅ | ✅ | ✅ |
| Unshare own meal | ✅ | ✅ | ✅ |
| View family shared meals | ✅ | ✅ | ✅ |
| View all member meals | ❌ | ❌ | ✅ |
| View member preferences | ❌ | ❌ | ✅ |
| View member profiles | ❌ | ❌ | ✅ |
| Manage members | ❌ | ✅ | ✅ |
| Delete family | ❌ | ❌ | ✅ |

## Implementation Details

### Files Modified

1. **models/meal.py**
   - Added `shared_with_family` column (Boolean, default=False)

2. **schemas/meal.py**
   - Added `shared_with_family` field to `MealCreate` and `MealOut` schemas

3. **crud/meals.py**
   - Added `share_meal_with_family()` function
   - Added `unshare_meal_with_family()` function
   - Added `list_family_shared_meals()` function
   - Added `list_user_all_meals()` function

4. **routers/meals.py**
   - Added `POST /meals/me/{meal_id}/share` endpoint
   - Added `DELETE /meals/me/{meal_id}/share` endpoint
   - Added `GET /meals/family/{family_id}/shared` endpoint

5. **routers/families.py**
   - Added `GET /families/{family_id}/members/{user_id}/meals` endpoint
   - Added `GET /families/{family_id}/members/{user_id}/preferences` endpoint
   - Added `GET /families/{family_id}/members/{user_id}/profile` endpoint

### Database Migration

Run the migration to add the new column:
```bash
alembic upgrade head
```

To rollback:
```bash
alembic downgrade -1
```

## Usage Examples

### Example 1: Member Shares a Meal
```bash
# Share meal ID 123 with family
curl -X POST "http://localhost:8000/meals/me/123/share" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Example 2: View Family Shared Meals
```bash
# Get all meals shared in family ID 5
curl -X GET "http://localhost:8000/meals/family/5/shared" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Example 3: Family Owner Views Member Meals
```bash
# Owner views all meals from user ID 456 in family ID 5
curl -X GET "http://localhost:8000/families/5/members/456/meals" \
  -H "Authorization: Bearer OWNER_TOKEN"
```

### Example 4: Family Owner Views Member Preferences
```bash
# Owner views preferences of user ID 456 in family ID 5
curl -X GET "http://localhost:8000/families/5/members/456/preferences" \
  -H "Authorization: Bearer OWNER_TOKEN"
```

## Security Considerations

1. **Authorization Checks**
   - All endpoints verify user authentication via Bearer token
   - Family membership is validated for all family-related operations
   - Owner role is strictly enforced for sensitive endpoints

2. **Data Privacy**
   - Members can only share their own meals
   - Shared meals are read-only for other family members
   - Owner access is clearly communicated and limited to family context

3. **Input Validation**
   - Meal ownership is verified before sharing/unsharing
   - Family membership is validated for all operations
   - Role-based access control is enforced at the endpoint level

## Frontend Integration

### Recommended UI Components

1. **Personal Dashboard**
   - List user's own meals
   - Toggle button to share/unshare each meal
   - Filter to show "My Meals" vs "Shared with Family"

2. **Family Dashboard** (All Members)
   - View all meals shared by family members
   - Read-only display with creator information
   - Filter by meal type, cuisine, etc.

3. **Family Owner Dashboard** (Owners Only)
   - Separate section for owner-only features
   - Member list with expandable details
   - View individual member meals, preferences, and profiles
   - Clear "Read Only" indicators

### State Management

Consider tracking:
- `currentUser.role` in the family
- `isOwner` flag for conditional rendering
- `sharedMeals` array for family dashboard
- `memberData` object for owner dashboard

## Testing

### Test Coverage

1. **Unit Tests**
   - CRUD function tests
   - Schema validation tests

2. **Integration Tests**
   - Endpoint authorization tests
   - Family membership validation tests
   - Role-based access control tests

3. **Edge Cases**
   - Non-member trying to access family data
   - Member trying to share another member's meal
   - Admin trying to access owner-only endpoints
   - Meal without family_id being shared

## Future Enhancements

Potential improvements:
1. Meal comments/ratings from family members
2. Meal collaboration (multiple creators)
3. Meal history tracking
4. Bulk share/unshare operations
5. Family meal planning integration
6. Notification system for newly shared meals

## Support

For issues or questions:
1. Check the API documentation
2. Review error messages for specific guidance
3. Verify role permissions
4. Ensure database migration has been run

---

**Last Updated**: November 2, 2025
**Version**: 1.0.0
