**GitHub Copilot Prompt for Frontend Integration**

---

## Task: Implement Image Generation and Grocery Scanning Features

I need to integrate two new AI-powered features into my React/Next.js frontend that connect to my existing Freshly meal planning backend. The backend is already implemented and working.

### Backend API Endpoints (Already Implemented)

#### 1. Image Generation
```typescript
// POST /chat/generate-image
interface ImageGenerationRequest {
  prompt: string;
  size?: "256x256" | "512x512" | "1024x1024" | "1792x1024" | "1024x1792";
  quality?: "standard" | "hd";
  style?: "vivid" | "natural";
  conversation_id?: number | null;
}

interface ImageGenerationResponse {
  image_url: string;
  prompt: string;
  conversation_id: number;
  message_id: number;
}
```

#### 2. Grocery Scanning
```typescript
// POST /chat/scan-grocery
interface ImageScanRequest {
  image_data: string; // base64 encoded image
  conversation_id?: number | null;
}

interface GroceryItem {
  name: string;
  quantity: string;
  category: string;
  confidence: number;
}

interface ImageScanResponse {
  items: GroceryItem[];
  total_items: number;
  analysis_notes?: string;
  conversation_id: number;
  message_id: number;
}
```

### Requirements

#### Image Generation Component
Create a React component that:
1. **Input**: Text area for image prompt with character counter (max 1000 chars)
2. **Options**: Dropdown selectors for size, quality, and style
3. **Generate Button**: Triggers API call with loading state
4. **Result Display**: Shows generated image with download option
5. **Error Handling**: Displays user-friendly error messages
6. **Loading State**: Progress indicator during generation (can take 30-60 seconds)
7. **History**: Save generated images to local state/storage
8. **Integration**: Works with existing auth system (JWT tokens)

#### Grocery Scanner Component
Create a React component that:
1. **Image Upload**: File input or drag-and-drop area for photos
2. **Camera Integration**: Option to take photo directly (mobile-friendly)
3. **Preview**: Show uploaded image before scanning
4. **Scan Button**: Triggers API call with loading state
5. **Results Display**: 
   - List of identified items with quantities and categories
   - Confidence scores (color-coded: green >0.8, yellow 0.5-0.8, red <0.5)
   - Analysis notes from AI
6. **Export Options**: 
   - Add items to shopping list
   - Export as text/CSV
   - Save to meal planning system
7. **Error Handling**: Handle poor image quality, no items found, etc.
8. **Loading State**: Progress indicator during analysis (can take 20-40 seconds)

### Technical Implementation

#### API Service Functions
```typescript
// Create these service functions in utils/api.ts or similar

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://freshlybackend.duckdns.org';

export const generateImage = async (request: ImageGenerationRequest): Promise<ImageGenerationResponse> => {
  // Implementation with proper error handling and JWT auth
};

export const scanGroceryImage = async (request: ImageScanRequest): Promise<ImageScanResponse> => {
  // Implementation with proper error handling and JWT auth
};

// Utility function to convert File to base64
export const fileToBase64 = (file: File): Promise<string> => {
  // Implementation
};
```

#### State Management
- Use React hooks (useState, useEffect) or your existing state management
- Manage loading states, error states, and results
- Persist generated images and scan results locally

#### UI/UX Requirements
- **Responsive Design**: Works on desktop and mobile
- **Modern UI**: Clean, intuitive interface matching existing app design
- **Accessibility**: Proper ARIA labels, keyboard navigation
- **Performance**: Optimize image handling and API calls
- **User Feedback**: Clear loading indicators, success/error messages

#### Integration Points
- **Authentication**: Use existing JWT token system
- **Navigation**: Integrate with existing app navigation/routing
- **Styling**: Use existing CSS framework/design system
- **Shopping Lists**: Connect grocery scan results to existing shopping list functionality
- **Meal Planning**: Connect image generation to recipe/meal creation workflow

### Example Component Structure

```tsx
// Expected component structure - implement these:

export const ImageGenerator: React.FC = () => {
  // State for prompt, options, loading, result, error
  // API call handler
  // UI with form, options, and result display
};

export const GroceryScanner: React.FC = () => {
  // State for image, loading, results, error
  // File upload and base64 conversion
  // API call handler
  // UI with upload area, preview, and results
};

// Main page that includes both features
export const AIFeaturesPage: React.FC = () => {
  // Tabbed interface or side-by-side layout
  // Include both ImageGenerator and GroceryScanner
};
```

### Error Scenarios to Handle
- **401 Unauthorized**: Redirect to login
- **503 Service Unavailable**: Show "AI service temporarily unavailable"
- **400 Bad Request**: Show specific validation errors
- **Network Errors**: Show "Connection failed, please try again"
- **File Size/Format Errors**: Show "Please use JPEG/PNG under 10MB"
- **No Items Found**: Show "No grocery items detected in image"

### Success Criteria
1. ✅ Users can generate custom images from text prompts
2. ✅ Users can upload grocery photos and get structured item lists
3. ✅ Both features integrate seamlessly with existing app
4. ✅ Proper loading states and error handling
5. ✅ Mobile-responsive and accessible
6. ✅ Results can be saved/exported/integrated with app features

### Additional Features (Nice to Have)
- **Image Gallery**: View previously generated images
- **Scan History**: Review past grocery scans
- **Bulk Operations**: Process multiple grocery images
- **Smart Prompts**: Suggest image generation prompts based on recipes
- **Shopping List Integration**: One-click add scanned items to shopping lists
- **Recipe Creation**: Use generated images for custom recipes

---

**Note**: The backend API is fully implemented and working. Focus on creating polished, user-friendly React components that make these powerful AI features accessible and integrated into the existing Freshly meal planning application.
