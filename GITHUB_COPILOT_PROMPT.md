🎯 **COPY THIS EXACT PROMPT TO GITHUB COPILOT**

---

I need to implement three AI features in my React/Next.js meal planning app. The backend APIs are deployed and working at `https://freshlybackend.duckdns.org`.

## 🎨 Feature 1: AI Image Generation

**Endpoint:** `POST https://freshlybackend.duckdns.org/chat/generate-image`

Create a React component with:
- Text area for image prompt (placeholder: "A cozy kitchen with fresh vegetables...")
- Dropdowns for size ("1024x1024", "1792x1024", "1024x1792"), quality ("standard", "hd"), style ("vivid", "natural")
- Generate button with 30-60 second loading state
- Display generated image with download button
- Error handling for API failures

**Request format:**
```json
{
  "prompt": "A beautiful kitchen with fresh ingredients",
  "size": "1024x1024",
  "quality": "hd", 
  "style": "natural"
}
```

**Response format:**
```json
{
  "image_url": "https://...",
  "prompt": "...",
  "conversation_id": 123,
  "message_id": 456
}
```

## 🛒 Feature 2: Grocery Image Scanning  

**Endpoint:** `POST https://freshlybackend.duckdns.org/chat/scan-grocery`

Create a React component with:
- File upload with drag-and-drop (accept="image/*")
- Camera capture option for mobile
- Image preview before scanning
- Scan button with 20-40 second loading state
- Results showing items in cards/list with name, quantity, category
- Color-coded confidence scores (green >0.8, yellow 0.5-0.8, red <0.5)
- "Add to Shopping List" button for each item

**Request format:**
```json
{
  "image_data": "base64_encoded_image_string"
}
```

**Response format:**
```json
{
  "items": [
    {
      "name": "Red Delicious Apples",
      "quantity": "3 pieces", 
      "category": "fruits",
      "confidence": 0.95
    }
  ],
  "total_items": 1,
  "analysis_notes": "Good image quality"
}
```

## 🏠 Feature 3: Automatic Pantry Item Images

**How it works:** When users add items to their pantry, the backend automatically generates and stores food images.

**Backend Integration:** The pantry items API has been enhanced:
- When creating pantry items (`POST /pantry-items`), images are generated automatically in background
- Images are stored in Supabase storage bucket `pantry_items`
- Storage path: `{userID}/{itemId}/{nameOfItem}.jpg`
- Images are optimized for pantry display (512x512, natural style)

**Frontend Requirements:**
- Update pantry item cards/lists to display `image_url` when available
- Show placeholder/loading state while image is being generated
- Handle cases where image generation fails (fallback to default icon)
- Add image refresh option for existing items without images

**Enhanced Pantry Item Response:**
```json
{
  "id": 123,
  "ingredient_name": "Red Delicious Apples",
  "quantity": 5,
  "unit": "pieces",
  "category": "fruits",
  "image_url": "https://supabase.co/storage/pantry_items/456/123/red_delicious_apples.jpg",
  "created_at": "2025-10-31T10:00:00Z"
}
```

## 🔧 Technical Requirements:

**Authentication:** Add to all requests:
```javascript
headers: {
  'Authorization': `Bearer ${localStorage.getItem('token')}`,
  'Content-Type': 'application/json'
}
```

**File to Base64 conversion:**
```javascript
const fileToBase64 = (file) => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.readAsDataURL(file);
  });
};
```

**Error handling:** Handle 401 (redirect to login), 503 (service unavailable), 400 (bad request)

## 📱 UI Requirements:
- Modern, clean design with Tailwind CSS or styled-components
- Mobile-responsive layout
- Loading spinners with progress text
- Toast notifications for success/error
- Accessible with proper ARIA labels
- Dark/light theme support

## 📁 File Structure:
Create these files:
- `components/ImageGenerator.tsx` - Manual image generation component
- `components/GroceryScanner.tsx` - Grocery scanning component
- `components/PantryItemCard.tsx` - Enhanced pantry item display with auto-generated images
- `utils/aiApi.ts` - API functions for all AI features
- `pages/ai-features.tsx` - Main page with manual AI tools
- `hooks/usePantryImages.ts` - Hook for managing pantry item image states

**Update existing pantry components to:**
- Display `image_url` from pantry items API response
- Show loading states for images being generated
- Handle fallback when `image_url` is null/empty
- Add refresh option to regenerate images

Make components reusable, well-typed with TypeScript, and include comprehensive error handling. The UI should feel native to a modern meal planning application.
