# 🔧 Frontend Integration: Fix Avatar Upload CORS Issues

## 🚨 Current Issue
Avatar uploads are failing with CORS preflight errors due to custom headers. The backend has been updated to use JWT-only authentication.

## 📋 Required Frontend Changes

### 1. Remove Custom Header from Avatar Upload

**File to Update:** `src/user/uploadViaBackend.ts` (or wherever avatar upload is handled)

**Before (❌ Causes CORS Issues):**
```typescript
const res = await fetch(`${BASE_URL}/storage/avatar/proxy`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    'X-User-ID': appUserId, // ❌ Remove this line - causes CORS preflight to fail
  },
  body: formData,
});
```

**After (✅ Fixed):**
```typescript
const res = await fetch(`${BASE_URL}/storage/avatar/proxy`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    // ✅ No custom headers needed - user ID comes from JWT token
  },
  body: formData,
});
```

### 2. Complete Example Function

```typescript
export async function uploadAvatarViaProxy(
  file: File,
  token: string,
  appUserId: string // Keep for logging but don't send as header
): Promise<Response> {
  console.log(`[uploadAvatarViaProxy] Starting upload for userId: ${appUserId}`);
  console.log(`[uploadAvatarViaProxy] File size: ${file.size} bytes`);

  const formData = new FormData();
  formData.append('file', file);
  // ✅ Don't append user_id to FormData - backend gets it from JWT

  try {
    const res = await fetch(`${BASE_URL}/storage/avatar/proxy`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        // ✅ Removed: 'X-User-ID': appUserId,
      },
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
    }

    console.log(`[uploadAvatarViaProxy] Upload successful`);
    return res;
  } catch (error) {
    console.error(`[uploadAvatarViaProxy] Upload failed:`, error);
    throw error;
  }
}
```

## 🔍 What Changed on Backend

1. **✅ JWT-Only Authentication**: Backend extracts user ID from JWT token automatically
2. **✅ Removed Custom Headers**: `X-User-ID` removed from CORS allowed headers
3. **✅ Cleaner Security**: User ID now comes from verified JWT, not client header
4. **✅ No CORS Issues**: No custom headers = no preflight complications

## 🧪 Testing After Changes

After removing the `X-User-ID` header:

1. **✅ No CORS Errors**: Preflight requests should succeed
2. **✅ Normal Upload Flow**: Avatar uploads work as before
3. **✅ User Detection**: Backend automatically knows which user from JWT
4. **✅ Same Response**: API response format unchanged

## 📝 Summary of Changes

| Component | Change Required |
|-----------|----------------|
| **Headers** | Remove `'X-User-ID': appUserId` |
| **FormData** | Keep as-is (just the file) |
| **JWT Token** | Keep `Authorization: Bearer ${token}` |
| **API Response** | No change - same format |

## 🚀 Benefits

- 🔒 **More Secure**: User ID from verified JWT token, not client header
- 🌐 **No CORS Issues**: Simple requests don't trigger preflight
- 🧹 **Cleaner Code**: Less headers to manage
- ⚡ **Better Performance**: No preflight delay

## 💡 Why This Works

The backend storage endpoint uses:
```python
async def upload_avatar_proxy(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)  # Gets user from JWT
):
    user_id = str(current_user.id)  # Extracted from token automatically
```

So the user ID is automatically available from the JWT token - no need to send it separately!

---

**🎯 Action Required:** Remove the `'X-User-ID': appUserId` line from your avatar upload fetch request headers.
