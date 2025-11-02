# 📄 Receipt Scanner Service Documentation

**Module**: `services/receipt_scanner.py`  
**Purpose**: Extract detailed item information from grocery receipt images  
**Created**: November 2, 2025

---

## 🎯 Overview

The Receipt Scanner Service uses OpenAI's Vision API (GPT-4 Vision) to analyze receipt images and extract structured data about purchased items. It provides detailed information including item names, quantities, units, categories, and prices.

---

## ✨ Features

### Core Functionality
- ✅ **Item Extraction**: Extracts all items from receipt images
- ✅ **Detailed Information**: Returns name, quantity, unit, category, and price for each item
- ✅ **Store Detection**: Identifies store name if visible
- ✅ **Date Extraction**: Captures purchase date from receipt
- ✅ **Total Calculation**: Extracts total amount spent
- ✅ **Category Classification**: Automatically categorizes items
- ✅ **Confidence Scoring**: Provides confidence level for each extraction
- ✅ **Grouping & Analysis**: Built-in methods for organizing and analyzing items

### Supported Data Points

For each item:
1. **Name**: Item name as it appears on receipt
2. **Quantity**: Amount purchased (as a number)
3. **Unit**: Measurement unit (lb, oz, gallon, each, pack, etc.)
4. **Category**: Food category (Produce, Dairy, Meat, etc.)
5. **Price**: Item price (if visible on receipt)
6. **Confidence**: AI confidence score (0.0 to 1.0)

Receipt metadata:
- **Store Name**: Store/retailer name
- **Receipt Date**: Purchase date (YYYY-MM-DD format)
- **Total Amount**: Total receipt amount
- **Analysis Notes**: AI observations about receipt quality

---

## 📊 Data Models

### ReceiptItem
```python
class ReceiptItem(BaseModel):
    name: str                    # "Organic Bananas"
    quantity: float              # 2.5
    unit: str                    # "lb"
    category: str                # "Produce"
    price: Optional[float]       # 3.99
    confidence: float            # 0.95 (0.0 to 1.0)
```

### ReceiptScanResult
```python
class ReceiptScanResult(BaseModel):
    items: List[ReceiptItem]           # All extracted items
    total_items: int                   # Count of items
    store_name: Optional[str]          # "Kroger"
    receipt_date: Optional[str]        # "2025-11-02"
    total_amount: Optional[float]      # 45.67
    analysis_notes: Optional[str]      # "Clear receipt, all items legible"
```

---

## 🚀 Usage

### Basic Usage - Scan from File

```python
from services.receipt_scanner import receipt_scanner_service

# Scan a receipt image file
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Access results
print(f"Store: {result.store_name}")
print(f"Date: {result.receipt_date}")
print(f"Total: ${result.total_amount}")
print(f"Items: {result.total_items}")

# Iterate through items
for item in result.items:
    print(f"{item.name}: {item.quantity} {item.unit}")
    print(f"  Category: {item.category}")
    if item.price:
        print(f"  Price: ${item.price:.2f}")
    print(f"  Confidence: {item.confidence:.0%}")
```

### Scan from Base64

```python
import base64
from services.receipt_scanner import receipt_scanner_service

# Read and encode image
with open('receipt.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Scan receipt
result = await receipt_scanner_service.scan_receipt(
    image_data=image_data,
    detail_level="high"  # "low", "high", or "auto"
)

# Process results
for item in result.items:
    print(f"{item.name}: {item.quantity} {item.unit}")
```

### Group Items by Category

```python
# Scan receipt
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Group items by category
grouped = receipt_scanner_service.group_items_by_category(result.items)

for category, items in grouped.items():
    print(f"\n{category}:")
    for item in items:
        print(f"  - {item.name} ({item.quantity} {item.unit})")
```

### Calculate Category Spending

```python
# Scan receipt
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Calculate totals per category
totals = receipt_scanner_service.calculate_category_totals(result.items)

# Display sorted by spending
for category, total in sorted(totals.items(), key=lambda x: x[1], reverse=True):
    print(f"{category}: ${total:.2f}")
```

### Format for Database

```python
# Scan receipt
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Format items for database insertion
formatted_items = receipt_scanner_service.format_items_for_grocery_list(result.items)

# Add to database
for item_data in formatted_items:
    # Create database record
    pantry_item = PantryItem(
        user_id=current_user.id,
        name=item_data['name'],
        quantity=item_data['quantity'],
        unit=item_data['unit'],
        category=item_data['category']
    )
    db.add(pantry_item)
db.commit()
```

---

## 📋 API Reference

### ReceiptScannerService

#### `scan_receipt(image_data: str, detail_level: str = "high") -> ReceiptScanResult`
Scan a receipt from base64 encoded image.

**Parameters:**
- `image_data` (str): Base64 encoded image string
- `detail_level` (str): Vision API detail level ("low", "high", "auto")

**Returns:** `ReceiptScanResult` with all extracted items

**Raises:** `Exception` if scanning fails or API error occurs

---

#### `scan_receipt_from_file(file_path: str, detail_level: str = "high") -> ReceiptScanResult`
Convenience method to scan receipt from file path.

**Parameters:**
- `file_path` (str): Path to receipt image file
- `detail_level` (str): Vision API detail level

**Returns:** `ReceiptScanResult` with all extracted items

---

#### `format_items_for_grocery_list(items: List[ReceiptItem]) -> List[Dict[str, Any]]`
Format receipt items for adding to grocery list or pantry.

**Parameters:**
- `items` (List[ReceiptItem]): List of extracted items

**Returns:** List of dictionaries formatted for database insertion

---

#### `group_items_by_category(items: List[ReceiptItem]) -> Dict[str, List[ReceiptItem]]`
Group items by their category for easier organization.

**Parameters:**
- `items` (List[ReceiptItem]): List of extracted items

**Returns:** Dictionary mapping category names to lists of items

---

#### `calculate_category_totals(items: List[ReceiptItem]) -> Dict[str, float]`
Calculate total spending per category.

**Parameters:**
- `items` (List[ReceiptItem]): List of extracted items

**Returns:** Dictionary mapping category names to total amounts spent

---

## 📦 Categories

Items are automatically classified into these categories:

| Category | Examples |
|----------|----------|
| **Produce** | Fruits, vegetables, fresh herbs |
| **Dairy** | Milk, cheese, yogurt, eggs, butter |
| **Meat** | Beef, chicken, pork, fish, seafood |
| **Bakery** | Bread, pastries, baked goods |
| **Pantry** | Canned goods, dry goods, pasta, rice, beans |
| **Frozen** | Frozen meals, ice cream, frozen vegetables |
| **Beverages** | Soda, juice, coffee, tea, water |
| **Snacks** | Chips, cookies, crackers, candy |
| **Condiments** | Sauces, dressings, spices, oils |
| **Household** | Cleaning supplies, paper products |
| **Other** | Items that don't fit above categories |

---

## 📏 Units

Common measurement units returned:

### Weight
- `lb` - Pounds
- `oz` - Ounces
- `g` - Grams
- `kg` - Kilograms

### Volume
- `gallon` - Gallons
- `quart` - Quarts
- `liter` - Liters
- `fl oz` - Fluid ounces
- `ml` - Milliliters

### Count/Package
- `each` - Individual items
- `count` - Number of items
- `pack` - Package
- `box` - Box
- `bag` - Bag
- `can` - Can
- `bottle` - Bottle

---

## 🧪 Testing

### Test Script

```bash
# Test with a receipt image
python test_receipt_scanner.py /path/to/receipt.jpg
```

The test script will:
1. Scan the receipt image
2. Display all extracted items
3. Show store name, date, and total
4. Group items by category
5. Calculate spending by category
6. Provide usage examples

### Manual Testing

```python
import asyncio
from services.receipt_scanner import receipt_scanner_service

async def test():
    result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')
    
    print(f"Found {result.total_items} items")
    for item in result.items:
        print(f"- {item.name}: {item.quantity} {item.unit}")

asyncio.run(test())
```

---

## 💡 Integration Examples

### 1. Auto-Update Pantry from Receipt

```python
async def add_receipt_to_pantry(user_id: int, receipt_image: str, db: Session):
    """Add all items from receipt to user's pantry"""
    
    # Scan receipt
    result = await receipt_scanner_service.scan_receipt(receipt_image)
    
    # Add items to pantry
    for item in result.items:
        pantry_item = PantryItem(
            user_id=user_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            category=item.category,
            purchase_date=result.receipt_date,
            price=item.price
        )
        db.add(pantry_item)
    
    db.commit()
    
    return result.total_items
```

### 2. Generate Shopping List from Receipt

```python
async def receipt_to_shopping_list(user_id: int, receipt_image: str, db: Session):
    """Create a new shopping list based on receipt items"""
    
    # Scan receipt
    result = await receipt_scanner_service.scan_receipt(receipt_image)
    
    # Create shopping list
    shopping_list = GroceryList(
        user_id=user_id,
        name=f"From {result.store_name or 'Receipt'} - {result.receipt_date}",
        created_at=datetime.utcnow()
    )
    db.add(shopping_list)
    db.flush()
    
    # Add items
    for item in result.items:
        list_item = GroceryListItem(
            grocery_list_id=shopping_list.id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            category=item.category,
            purchased=True  # Already purchased
        )
        db.add(list_item)
    
    db.commit()
    
    return shopping_list
```

### 3. Track Spending Analytics

```python
async def analyze_receipt_spending(receipt_image: str):
    """Analyze spending patterns from receipt"""
    
    # Scan receipt
    result = await receipt_scanner_service.scan_receipt(receipt_image)
    
    # Calculate category totals
    category_totals = receipt_scanner_service.calculate_category_totals(result.items)
    
    # Analyze
    analysis = {
        "store": result.store_name,
        "date": result.receipt_date,
        "total": result.total_amount,
        "items": result.total_items,
        "category_breakdown": category_totals,
        "avg_price_per_item": result.total_amount / result.total_items if result.total_items > 0 else 0
    }
    
    return analysis
```

---

## ⚙️ Configuration

The service uses these settings from `core/settings.py`:

```python
OPENAI_API_KEY: str  # Required for Vision API access
```

### Vision API Detail Levels

- **"low"**: Faster, less detailed analysis
- **"high"**: Slower, more detailed analysis (recommended for receipts)
- **"auto"**: Let OpenAI decide based on image

---

## 🔒 Security & Privacy

- ✅ Receipt images are sent to OpenAI's Vision API for processing
- ✅ No receipt data is stored by OpenAI (per their API terms)
- ✅ Images should be validated before processing
- ✅ Consider PII implications (credit card numbers, etc.)
- ✅ Implement proper authentication and authorization
- ✅ Log access to receipt scanning functionality

---

## ⚡ Performance

- **Processing Time**: 2-5 seconds per receipt (depends on image size and complexity)
- **Max Image Size**: 20MB (OpenAI limit), but recommend < 5MB for reliability
- **Token Usage**: ~1000-2000 tokens per receipt (varies with detail level)
- **Accuracy**: High for clear, well-lit receipts; lower for damaged/blurry receipts

### Optimization Tips

1. **Image Quality**: Use high-res, well-lit receipt photos
2. **Detail Level**: Use "high" for complex receipts, "low" for simple ones
3. **Batch Processing**: Process multiple receipts in parallel with asyncio
4. **Caching**: Cache results to avoid re-scanning same receipts

---

## 🐛 Error Handling

### Common Issues

**Empty Items List**
```python
if result.total_items == 0:
    logger.warning("No items found on receipt")
    # Check analysis_notes for explanation
    if "unclear" in result.analysis_notes.lower():
        # Receipt was too blurry/damaged
        pass
```

**Low Confidence Scores**
```python
low_confidence_items = [
    item for item in result.items 
    if item.confidence < 0.7
]

if low_confidence_items:
    logger.warning(f"{len(low_confidence_items)} items have low confidence")
    # May need manual review
```

**Missing Prices**
```python
items_without_prices = [
    item for item in result.items 
    if item.price is None
]

# Some receipts don't show individual prices
# Only subtotal and tax shown
```

---

## 📈 Example Output

```python
{
  "items": [
    {
      "name": "Organic Bananas",
      "quantity": 2.5,
      "unit": "lb",
      "category": "Produce",
      "price": 1.49,
      "confidence": 0.95
    },
    {
      "name": "Whole Milk",
      "quantity": 1.0,
      "unit": "gallon",
      "category": "Dairy",
      "price": 3.99,
      "confidence": 0.98
    },
    {
      "name": "Ground Beef",
      "quantity": 2.0,
      "unit": "lb",
      "category": "Meat",
      "price": 8.99,
      "confidence": 0.92
    },
    {
      "name": "Sliced Bread",
      "quantity": 1.0,
      "unit": "loaf",
      "category": "Bakery",
      "price": 2.49,
      "confidence": 0.96
    }
  ],
  "total_items": 4,
  "store_name": "Kroger",
  "receipt_date": "2025-11-02",
  "total_amount": 16.96,
  "analysis_notes": "Clear receipt, all items legible"
}
```

---

## 🎯 Use Cases

1. **Automatic Pantry Updates**: Scan receipt after shopping to auto-update pantry
2. **Expense Tracking**: Track grocery spending by category over time
3. **Shopping Pattern Analysis**: Analyze what users buy most frequently
4. **Recipe Suggestions**: Suggest recipes based on purchased items
5. **Budget Management**: Monitor spending vs budget goals
6. **Inventory Management**: Keep accurate inventory of purchased items
7. **Price Comparison**: Track price changes across different stores/dates

---

## 🚀 Future Enhancements

Potential improvements:
- [ ] Support for multi-page receipts
- [ ] Barcode/SKU extraction
- [ ] Duplicate item detection and merging
- [ ] Sales/discount detection
- [ ] Nutritional information lookup
- [ ] Store-specific optimizations
- [ ] Receipt validation (totals match sum of items)
- [ ] Historical price trend analysis

---

## 📞 Support

For issues or questions:
1. Check test script: `python test_receipt_scanner.py receipt.jpg`
2. Review `analysis_notes` in results for AI observations
3. Verify image quality (clear, well-lit, not blurry)
4. Check OpenAI API key is configured correctly
5. Review logs for detailed error traces

---

**Created**: November 2, 2025  
**Service**: `receipt_scanner_service`  
**Status**: ✅ Production Ready  
**Test Coverage**: ✅ Test script provided
