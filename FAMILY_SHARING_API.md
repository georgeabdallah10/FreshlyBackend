# Family Meal Sharing API

Quick reference for frontend integration.

## New Endpoints

### 1. Share Meal with Family
**POST** `/meals/me/{meal_id}/share`

Shares your meal with your family members.

**Response:**
```json
{
  "id": 123,
  "name": "Spaghetti Carbonara",
  "sharedWithFamily": true,
  ...
}
```

**Errors:**
- `400` - Meal already shared or meal not in a family
- `404` - Meal not found or unauthorized

---

### 2. Unshare Meal from Family
**DELETE** `/meals/me/{meal_id}/share`

Stops sharing your meal with family.

**Response:** Updated meal with `sharedWithFamily: false`

**Errors:**
- `400` - Meal not currently shared
- `404` - Meal not found or unauthorized

---

### 3. Get Family Shared Meals
**GET** `/meals/family/{family_id}/shared`

Get all meals shared by family members.

**Response:**
```json
[
  {
    "id": 123,
    "name": "Spaghetti Carbonara",
    "createdByUserId": 45,
    "sharedWithFamily": true,
    ...
  }
]
```

**Errors:**
- `403` - Not a member of this family

---

### 4. View Member's Meals (Owner Only)
**GET** `/families/{family_id}/members/{user_id}/meals`

Family owners can view all meals created by a member (read-only).

**Response:** Array of meals

**Errors:**
- `403` - Not family owner

---

### 5. View Member's Preferences (Owner Only)
**GET** `/families/{family_id}/members/{user_id}/preferences`

Family owners can view a member's dietary preferences.

**Response:**
```json
{
  "id": 1,
  "userId": 45,
  "dietCodes": ["vegetarian", "gluten-free"],
  "allergenIngredientIds": [12, 34],
  "dislikedIngredientIds": [56],
  "goal": "weight_loss",
  "calorieTarget": 1800
}
```

**Errors:**
- `403` - Not family owner

---

### 6. View Member's Profile (Owner Only)
**GET** `/families/{family_id}/members/{user_id}/profile`

Family owners can view a member's profile information.

**Response:**
```json
{
  "id": 45,
  "email": "user@example.com",
  "name": "John Doe",
  "phoneNumber": "+1234567890",
  "location": "New York, NY",
  "avatarPath": "avatars/user-45.jpg",
  "status": "active",
  "isVerified": true
}
```

**Errors:**
- `403` - Not family owner

---

## Schema Changes

### MealCreate / MealOut
Added field:
- `sharedWithFamily` (boolean, default: false)

---

## Permission Model

### All Family Members Can:
- Share/unshare their own meals
- View meals shared by other members
- View their own data

### Family Owners Can:
- Everything members can do, PLUS:
- View all meals of any member (read-only)
- View preferences of any member (read-only)
- View profile of any member (read-only)

---

## Usage Example

```typescript
// Share a meal
await fetch(`/meals/me/${mealId}/share`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});

// Get family shared meals
const response = await fetch(`/meals/family/${familyId}/shared`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const sharedMeals = await response.json();

// Owner view member meals
const response = await fetch(`/families/${familyId}/members/${userId}/meals`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const memberMeals = await response.json();
```

---

## Database Migration

Run before deploying:
```bash
alembic upgrade head
```
