# 🔧 Frontend Fix: Remove X-User-ID Header for Avatar Upload

## 🚨 Issue
Avatar uploads are failing with CORS preflight errors because of the custom `X-User-ID` header.

## ✅ Solution
The backend already uses JWT authentication properly. The frontend just needs to **remove the custom header**.

## 📝 Required Frontend Changes

### Before (Causes CORS Issues):
```typescript
// ❌ This causes CORS preflight to fail
const res = await fetch(`${BASE_URL}/storage/avatar/proxy`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    'X-User-ID': appUserId, // ❌ Remove this line
  },
  body: formData,
});
```

### After (Fixed):
```typescript
// ✅ This works without CORS issues
const res = await fetch(`${BASE_URL}/storage/avatar/proxy`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    // ✅ No custom headers needed
  },
  body: formData,
});
```

## 🔍 What Changed on Backend

1. **✅ JWT Authentication**: Backend uses `Depends(get_current_user)` to get user from token
2. **✅ No Custom Headers**: Backend gets `user_id` from the JWT token, not headers
3. **✅ CORS Fixed**: Removed `X-User-ID` from allowed headers to prevent preflight issues

## 📂 File to Update

Update your avatar upload function (likely in `src/user/uploadViaBackend.ts` or similar):

```typescript
// Find this function and remove the X-User-ID header
export async function uploadAvatarViaProxy(
  file: File,
  token: string,
  appUserId: string // Can keep this parameter for logging but don't send as header
) {
  const formData = new FormData();
  formData.append('file', file);
  // ✅ Don't append user_id to FormData - it comes from JWT token

  const res = await fetch(`${BASE_URL}/storage/avatar/proxy`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      // ✅ Removed: 'X-User-ID': appUserId,
    },
    body: formData,
  });

  return res;
}
```

## 🧪 Testing

After making this change:
1. ✅ No more CORS preflight errors
2. ✅ Avatar uploads should work normally
3. ✅ User ID is automatically extracted from JWT token on backend

## 📋 Summary

- **Remove**: `'X-User-ID': appUserId` from headers
- **Keep**: `Authorization: Bearer ${token}` header
- **Keep**: FormData with the file
- **Result**: Clean uploads without CORS issues

The backend handles everything automatically through JWT authentication!
