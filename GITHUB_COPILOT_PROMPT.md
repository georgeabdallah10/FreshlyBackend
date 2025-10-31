🎯 **COPY THIS EXACT PROMPT TO GITHUB COPILOT**

---

I need to implement two AI features in my React/Next.js meal planning app. The backend APIs are deployed and working at `https://freshlybackend.duckdns.org`.

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
- `components/ImageGenerator.tsx`
- `components/GroceryScanner.tsx` 
- `utils/aiApi.ts` (API functions)
- `pages/ai-features.tsx` (main page)

Make components reusable, well-typed with TypeScript, and include comprehensive error handling. The UI should feel native to a modern meal planning application.
