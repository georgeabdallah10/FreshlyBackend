# Frontend Debug Prompt for Sync Pantry Endpoint

Use this prompt in Cursor for your frontend codebase:

---

**Prompt:**

Check if the sync pantry endpoint is working properly in the frontend. The endpoint is:

- **Method:** `POST`
- **URL:** `/grocery-lists/{list_id}/sync-pantry`
- **Authentication:** Requires JWT token in Authorization header
- **Request Body:** None (empty body)
- **Response:** 
  ```typescript
  {
    items_removed: number,
    items_updated: number,
    remaining_items: RemainingItem[],
    message: string
  }
  
  interface RemainingItem {
    ingredient_id: number;
    ingredient_name: string;
    quantity: number | null;      // May be null if only note is available
    unit_code: string | null;     // May be null if only note is available
    canonical_quantity: number | null;
    canonical_unit: string | null;
    note: string | null;          // Display text like "2 cups" for items without parsed quantities
  }
  ```

**Things to verify:**

1. **API Call Implementation:**
   - Find where `sync-pantry` or `syncPantry` is called in the frontend
   - Verify the HTTP method is `POST` (not GET)
   - Verify the URL includes the `list_id` in the path: `/grocery-lists/{list_id}/sync-pantry`
   - Verify no request body is being sent (should be empty or null)
   - Verify the Authorization header with JWT token is included

2. **Error Handling:**
   - Check for 403 errors: "Only the list creator can sync with pantry" - this means the user is not the creator
   - Check for 404 errors: "List not found" - verify the list_id is correct
   - Check for 400 errors: Should show the error detail message
   - Verify error messages are being displayed to the user

3. **Response Handling:**
   - After successful sync, verify the response contains `items_removed`, `items_updated`, `remaining_items`, and `message`
   - The `remaining_items` array contains all items still needed after pantry sync
   - For items with parsed quantities: use `quantity` and `unit_code` fields
   - For items without parsed quantities: use the `note` field (e.g., "2 cups")
   - Check if the frontend is refreshing/updating the grocery list after sync
   - Verify the UI reflects the changes (items removed or quantities updated)

4. **Authorization Check:**
   - Verify the user calling sync is the list creator:
     - For personal lists: user must be the `owner_user_id`
     - For family lists: user must be the `created_by_user_id`
   - Check if the frontend is checking this before showing the sync button

5. **Common Issues to Check:**
   - Is the list_id being passed correctly in the URL?
   - Is the JWT token valid and not expired?
   - Is the request being made to the correct base URL?
   - Are CORS headers properly configured?
   - Is the response being parsed correctly (JSON)?
   - Are there any network errors in the browser console?

6. **Testing:**
   - Test with a personal grocery list where the user is the owner
   - Test with a family grocery list where the user is the creator
   - Test with a family grocery list where the user is NOT the creator (should get 403)
   - Verify the grocery list items change after sync (items removed or quantities reduced)

**Expected Behavior:**
- Items fully covered by pantry should be removed from the list
- Items partially covered should have their quantities reduced
- Only unchecked items are processed (checked items are skipped)
- The list's `updated_at` timestamp should be updated

Please check the implementation and fix any issues found.

