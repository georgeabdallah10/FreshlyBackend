"""
Receipt Scanner Service

Processes receipt images to extract purchased items with detailed information.
Uses OpenAI Vision API to analyze receipts and return structured data about items.
"""
import logging
import base64
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from core.settings import settings

logger = logging.getLogger(__name__)


class ReceiptItem(BaseModel):
    """Model for a single item from a receipt"""
    name: str = Field(..., description="Item name as it appears on receipt")
    quantity: float = Field(..., description="Quantity purchased")
    unit: str = Field(..., description="Unit of measurement (e.g., 'lb', 'oz', 'each', 'gallon')")
    category: str = Field(..., description="Food category (e.g., 'Dairy', 'Produce', 'Meat')")
    price: Optional[float] = Field(None, description="Item price if visible on receipt")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")


class ReceiptScanResult(BaseModel):
    """Result of receipt scanning"""
    items: List[ReceiptItem] = Field(default_factory=list)
    total_items: int = Field(..., description="Total number of items found")
    store_name: Optional[str] = Field(None, description="Store name if detected")
    receipt_date: Optional[str] = Field(None, description="Purchase date if detected")
    total_amount: Optional[float] = Field(None, description="Total receipt amount if detected")
    analysis_notes: Optional[str] = Field(None, description="Additional observations")


class ReceiptScannerService:
    """Service for scanning receipts and extracting item information"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # Use GPT-4 Vision model
    
    async def scan_receipt(
        self, 
        image_data: str,
        detail_level: str = "high"
    ) -> ReceiptScanResult:
        """
        Scan a receipt image and extract all purchased items.
        
        Args:
            image_data: Base64 encoded image string
            detail_level: Vision API detail level ("low", "high", "auto")
            
        Returns:
            ReceiptScanResult with all extracted items
            
        Raises:
            Exception: If scanning fails or API error occurs
        """
        logger.info("Starting receipt scan")
        
        try:
            # Prepare the prompt for receipt analysis
            prompt = self._build_receipt_analysis_prompt()
            
            # Call OpenAI Vision API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing grocery receipts and extracting item information."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                    "detail": detail_level
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            # Parse the AI response
            result = self._parse_ai_response(response)
            
            logger.info(f"Receipt scan completed: {result.total_items} items found")
            return result
            
        except Exception as e:
            logger.error(f"Receipt scanning failed: {e}", exc_info=True)
            raise
    
    def _build_receipt_analysis_prompt(self) -> str:
        """Build the prompt for receipt analysis"""
        return """
Analyze this grocery receipt image and extract ALL items purchased.

For each item, provide:
1. **name**: The exact item name as it appears on the receipt
2. **quantity**: The number/amount purchased (as a number)
3. **unit**: The unit of measurement:
   - For produce: "lb" (pounds), "oz" (ounces), "each" (individual items)
   - For liquids: "gallon", "quart", "liter", "fl oz"
   - For packaged goods: "pack", "box", "bag", "can", "bottle"
   - For count items: "each", "count"
4. **category**: Classify into one of these categories:
   - Produce (fruits, vegetables)
   - Dairy (milk, cheese, yogurt, eggs)
   - Meat (beef, chicken, pork, fish, seafood)
   - Bakery (bread, pastries, baked goods)
   - Pantry (canned goods, dry goods, pasta, rice, beans)
   - Frozen (frozen meals, ice cream, frozen vegetables)
   - Beverages (soda, juice, coffee, tea)
   - Snacks (chips, cookies, crackers, candy)
   - Condiments (sauces, dressings, spices, oils)
   - Household (cleaning supplies, paper products)
   - Other (anything that doesn't fit above)
5. **price**: The item price if clearly visible (null if not visible)
6. **confidence**: How confident you are about this extraction (0.0 to 1.0)

Also extract:
- **store_name**: The store name if visible
- **receipt_date**: The purchase date if visible (format: YYYY-MM-DD)
- **total_amount**: The total receipt amount if visible

Return the data in this JSON format:
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
      "quantity": 1,
      "unit": "gallon",
      "category": "Dairy",
      "price": 3.99,
      "confidence": 0.98
    }
  ],
  "store_name": "Kroger",
  "receipt_date": "2025-11-02",
  "total_amount": 45.67,
  "analysis_notes": "Clear receipt, all items legible"
}

IMPORTANT:
- Extract EVERY item from the receipt, even if small or unclear
- If quantity is not specified, assume 1
- If unit is not clear, use "each" for countable items or your best guess
- Be as accurate as possible with item names and prices
- Only include actual grocery/food items, not subtotals or taxes
- If the receipt is unclear or damaged, note it in analysis_notes
"""
    
    def _parse_ai_response(self, response) -> ReceiptScanResult:
        """Parse OpenAI API response into ReceiptScanResult"""
        import json
        
        try:
            # Extract the message content
            content = response.choices[0].message.content
            
            # Try to find JSON in the response
            # Sometimes the AI wraps JSON in markdown code blocks
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            # Parse JSON
            data = json.loads(content)
            
            # Convert to ReceiptScanResult
            items = [ReceiptItem(**item) for item in data.get("items", [])]
            
            result = ReceiptScanResult(
                items=items,
                total_items=len(items),
                store_name=data.get("store_name"),
                receipt_date=data.get("receipt_date"),
                total_amount=data.get("total_amount"),
                analysis_notes=data.get("analysis_notes")
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response content: {response.choices[0].message.content}")
            
            # Return empty result if parsing fails
            return ReceiptScanResult(
                items=[],
                total_items=0,
                analysis_notes=f"Failed to parse receipt: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}", exc_info=True)
            raise
    
    async def scan_receipt_from_file(
        self, 
        file_path: str,
        detail_level: str = "high"
    ) -> ReceiptScanResult:
        """
        Convenience method to scan receipt from file path.
        
        Args:
            file_path: Path to receipt image file
            detail_level: Vision API detail level
            
        Returns:
            ReceiptScanResult with all extracted items
        """
        import aiofiles
        
        async with aiofiles.open(file_path, 'rb') as f:
            contents = await f.read()
            image_data = base64.b64encode(contents).decode('utf-8')
            return await self.scan_receipt(image_data, detail_level)
    
    def format_items_for_grocery_list(self, items: List[ReceiptItem]) -> List[Dict[str, Any]]:
        """
        Format receipt items for adding to grocery list or pantry.
        
        Args:
            items: List of ReceiptItem objects
            
        Returns:
            List of dictionaries formatted for database insertion
        """
        formatted_items = []
        
        for item in items:
            formatted_items.append({
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "category": item.category,
                "price": item.price,
                "confidence": item.confidence
            })
        
        return formatted_items
    
    def group_items_by_category(self, items: List[ReceiptItem]) -> Dict[str, List[ReceiptItem]]:
        """
        Group items by their category for easier organization.
        
        Args:
            items: List of ReceiptItem objects
            
        Returns:
            Dictionary mapping category names to lists of items
        """
        grouped = {}
        
        for item in items:
            category = item.category
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)
        
        return grouped
    
    def calculate_category_totals(self, items: List[ReceiptItem]) -> Dict[str, float]:
        """
        Calculate total spending per category.
        
        Args:
            items: List of ReceiptItem objects
            
        Returns:
            Dictionary mapping category names to total amounts spent
        """
        totals = {}
        
        for item in items:
            category = item.category
            if item.price is not None:
                if category not in totals:
                    totals[category] = 0.0
                totals[category] += item.price
        
        return totals


# Singleton instance
receipt_scanner_service = ReceiptScannerService()
