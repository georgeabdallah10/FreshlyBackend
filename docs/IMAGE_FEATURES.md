# Image Features Documentation

## Overview

The Freshly Backend now includes two powerful AI-powered image features:

1. **Image Generation** - Create custom images from text descriptions
2. **Grocery Scanning** - Automatically identify and categorize grocery items from photos

Both features integrate seamlessly with the existing chat system and maintain conversation history.

## 🎨 Image Generation

### Endpoint
```
POST /chat/generate-image
```

### Authentication
Requires valid JWT token in Authorization header.

### Request Schema
```json
{
  "prompt": "string",                    // Required: Text description of desired image
  "size": "1024x1024",                  // Optional: Image dimensions
  "quality": "standard",                // Optional: Image quality
  "style": "vivid",                     // Optional: Image style
  "conversation_id": 123                // Optional: Existing conversation ID
}
```

### Size Options
- `256x256` - Small square
- `512x512` - Medium square  
- `1024x1024` - Large square (default)
- `1792x1024` - Wide landscape
- `1024x1792` - Tall portrait

### Quality Options
- `standard` - Standard quality (default)
- `hd` - High definition (higher cost)

### Style Options
- `vivid` - Hyper-real and dramatic (default)
- `natural` - More natural, less hyper-real

### Response Schema
```json
{
  "image_url": "https://...",           // Generated image URL
  "prompt": "original prompt text",      // Echo of input prompt
  "conversation_id": 123,               // Conversation ID
  "message_id": 456                     // Message ID for this generation
}
```

### Usage Examples

**Basic Usage:**
```bash
curl -X POST "https://api.freshly.com/chat/generate-image" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A modern kitchen with fresh vegetables on marble countertops"
  }'
```

**Advanced Usage:**
```bash
curl -X POST "https://api.freshly.com/chat/generate-image" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Elegant meal prep containers with colorful healthy foods",
    "size": "1792x1024",
    "quality": "hd",
    "style": "natural",
    "conversation_id": 123
  }'
```

## 🛒 Grocery Scanning

### Endpoint
```
POST /chat/scan-grocery
```

### Authentication
Requires valid JWT token in Authorization header.

### Request Schema
```json
{
  "image_data": "base64_encoded_image",  // Required: Base64 encoded image
  "conversation_id": 123                 // Optional: Existing conversation ID
}
```

### Supported Image Formats
- JPEG
- PNG
- WebP
- Base64 encoded

### Response Schema
```json
{
  "items": [
    {
      "name": "Red Delicious Apples",     // Specific item name
      "quantity": "3 pieces",             // Estimated quantity
      "category": "fruits",               // Food category
      "confidence": 0.95                  // AI confidence (0.0-1.0)
    }
  ],
  "total_items": 2,                      // Total number of items found
  "analysis_notes": "Good lighting...",  // AI observations about image
  "conversation_id": 123,                // Conversation ID
  "message_id": 456                      // Message ID for this scan
}
```

### Categories
The AI categorizes items into these categories:
- `fruits`
- `vegetables` 
- `dairy`
- `meat`
- `snacks`
- `beverages`
- `pantry` (dry goods, canned items)
- `frozen`
- `bakery`
- `condiments`

### Usage Example

**JavaScript/TypeScript:**
```javascript
// Convert image file to base64
const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      // Remove data:image/jpeg;base64, prefix
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = error => reject(error);
  });
};

// Scan grocery image
const scanGroceries = async (imageFile) => {
  const base64Image = await fileToBase64(imageFile);
  
  const response = await fetch('/chat/scan-grocery', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image_data: base64Image
    })
  });
  
  const result = await response.json();
  console.log(`Found ${result.total_items} items:`, result.items);
};
```

**cURL:**
```bash
# First, convert image to base64
IMAGE_BASE64=$(base64 -i grocery_photo.jpg)

curl -X POST "https://api.freshly.com/chat/scan-grocery" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"image_data\": \"$IMAGE_BASE64\"
  }"
```

## Integration with Chat System

Both features integrate with the existing chat conversation system:

1. **New Conversations**: If no `conversation_id` is provided, a new conversation is created automatically
2. **Existing Conversations**: Provide `conversation_id` to add to existing chat thread
3. **Message History**: All generations and scans are saved as chat messages
4. **Conversation Management**: Use existing chat endpoints to view, update, or delete conversations

## Error Handling

### Common Error Responses

**Authentication Error (401):**
```json
{
  "error": "Not authenticated",
  "correlation_id": "abc123",
  "status_code": 401
}
```

**Service Unavailable (503):**
```json
{
  "error": "Chat service is not configured. OpenAI API key is missing.",
  "correlation_id": "def456", 
  "status_code": 503
}
```

**Image Generation Failed (400):**
```json
{
  "error": "Image generation failed: Invalid prompt",
  "correlation_id": "ghi789",
  "status_code": 400
}
```

**Image Analysis Failed (400):**
```json
{
  "error": "Image analysis failed: Unsupported image format",
  "correlation_id": "jkl012",
  "status_code": 400
}
```

## Rate Limiting

- Image generation: Limited by OpenAI API quotas
- Grocery scanning: Limited by OpenAI Vision API quotas
- Standard rate limiting applies per user account

## Best Practices

### Image Generation
1. **Descriptive Prompts**: Use detailed, specific descriptions for better results
2. **Size Selection**: Choose appropriate size for intended use case
3. **Quality vs Cost**: Use HD quality only when necessary (higher API cost)
4. **Conversation Context**: Link related generations in same conversation

### Grocery Scanning
1. **Image Quality**: Use well-lit, clear photos for best results
2. **Angle**: Shoot from above with items spread out when possible
3. **Focus**: Ensure items are in focus and not heavily obscured
4. **File Size**: Optimize images before base64 encoding to reduce payload size

### Frontend Integration
1. **Loading States**: Image operations can take 10-60 seconds
2. **Error Handling**: Implement robust error handling for API failures
3. **Caching**: Cache generated images on client side when appropriate
4. **User Feedback**: Show progress indicators during processing

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7
```

### Requirements
- OpenAI API account with DALL-E and Vision API access
- Sufficient API credits for image operations
- Database storage for conversation history

## API Limits

### OpenAI Limits
- DALL-E 3: 5 images per minute (varies by plan)
- Vision API: 100 requests per minute (varies by plan)
- Token limits apply to Vision API prompts

### Backend Limits
- Maximum image size: 20MB for upload
- Base64 payload limit: ~27MB (after encoding)
- Request timeout: 60 seconds

## Frontend Implementation Examples

### React Component for Image Generation
```jsx
const ImageGenerator = () => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const generateImage = async () => {
    setLoading(true);
    try {
      const response = await fetch('/chat/generate-image', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          size: '1024x1024',
          quality: 'hd'
        })
      });
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input 
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe the image you want..."
      />
      <button onClick={generateImage} disabled={loading}>
        {loading ? 'Generating...' : 'Generate Image'}
      </button>
      {result && <img src={result.image_url} alt="Generated" />}
    </div>
  );
};
```

### React Component for Grocery Scanning
```jsx
const GroceryScanner = () => {
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState(null);

  const handleImageUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setScanning(true);
    try {
      const base64 = await fileToBase64(file);
      
      const response = await fetch('/chat/scan-grocery', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_data: base64
        })
      });
      
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Scan failed:', error);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div>
      <input 
        type="file" 
        accept="image/*"
        onChange={handleImageUpload}
        disabled={scanning}
      />
      {scanning && <p>Scanning image...</p>}
      {results && (
        <div>
          <h3>Found {results.total_items} items:</h3>
          {results.items.map((item, index) => (
            <div key={index}>
              <strong>{item.name}</strong> - {item.quantity} 
              <span>({item.category})</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```
