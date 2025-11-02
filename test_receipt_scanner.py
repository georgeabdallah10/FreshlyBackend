#!/usr/bin/env python3
"""
Test script for Receipt Scanner Service

Tests the receipt scanning functionality that extracts items from receipt images.
"""
import asyncio
import base64
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.receipt_scanner import receipt_scanner_service, ReceiptScanResult


async def test_scan_receipt_from_file(image_path: str):
    """Test scanning a receipt from an image file"""
    print("=" * 80)
    print("RECEIPT SCANNER TEST")
    print("=" * 80)
    print()
    
    image_file = Path(image_path)
    
    if not image_file.exists():
        print(f"❌ ERROR: Image file not found: {image_path}")
        print("Please provide a valid receipt image file path")
        return
    
    print(f"📄 Receipt image: {image_file.name}")
    print(f"   Size: {image_file.stat().st_size / 1024:.2f} KB")
    print()
    
    try:
        # Scan the receipt
        print("🔍 Scanning receipt...")
        result = await receipt_scanner_service.scan_receipt_from_file(str(image_file))
        
        print("✅ Scan completed!")
        print()
        
        # Display results
        print("=" * 80)
        print("RECEIPT INFORMATION")
        print("=" * 80)
        
        if result.store_name:
            print(f"🏪 Store: {result.store_name}")
        
        if result.receipt_date:
            print(f"📅 Date: {result.receipt_date}")
        
        if result.total_amount:
            print(f"💰 Total: ${result.total_amount:.2f}")
        
        print(f"📦 Items Found: {result.total_items}")
        print()
        
        # Display items
        if result.items:
            print("=" * 80)
            print("ITEMS PURCHASED")
            print("=" * 80)
            print()
            
            for i, item in enumerate(result.items, 1):
                print(f"{i}. {item.name}")
                print(f"   Quantity: {item.quantity} {item.unit}")
                print(f"   Category: {item.category}")
                if item.price:
                    print(f"   Price: ${item.price:.2f}")
                print(f"   Confidence: {item.confidence:.0%}")
                print()
        else:
            print("⚠️  No items found on receipt")
            print()
        
        # Display analysis notes
        if result.analysis_notes:
            print("=" * 80)
            print("ANALYSIS NOTES")
            print("=" * 80)
            print(result.analysis_notes)
            print()
        
        # Show category breakdown
        print("=" * 80)
        print("CATEGORY BREAKDOWN")
        print("=" * 80)
        print()
        
        grouped = receipt_scanner_service.group_items_by_category(result.items)
        for category, items in sorted(grouped.items()):
            print(f"📂 {category}: {len(items)} items")
            for item in items:
                print(f"   - {item.name} ({item.quantity} {item.unit})")
        print()
        
        # Show spending by category
        if any(item.price for item in result.items):
            print("=" * 80)
            print("SPENDING BY CATEGORY")
            print("=" * 80)
            print()
            
            totals = receipt_scanner_service.calculate_category_totals(result.items)
            for category, total in sorted(totals.items(), key=lambda x: x[1], reverse=True):
                print(f"💵 {category}: ${total:.2f}")
            print()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def test_scan_receipt_from_base64(image_path: str):
    """Test scanning a receipt using base64 encoded image"""
    print("=" * 80)
    print("BASE64 RECEIPT SCANNER TEST")
    print("=" * 80)
    print()
    
    image_file = Path(image_path)
    
    if not image_file.exists():
        print(f"❌ ERROR: Image file not found: {image_path}")
        return
    
    try:
        # Read and encode image
        with open(image_file, 'rb') as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"📄 Receipt image: {image_file.name}")
        print(f"   Original size: {len(image_bytes)} bytes")
        print(f"   Base64 size: {len(image_base64)} characters")
        print()
        
        # Scan the receipt
        print("🔍 Scanning receipt...")
        result = await receipt_scanner_service.scan_receipt(image_base64)
        
        print(f"✅ Scan completed! Found {result.total_items} items")
        print()
        
        # Display simplified results
        for i, item in enumerate(result.items, 1):
            price_str = f" - ${item.price:.2f}" if item.price else ""
            print(f"{i}. {item.name}: {item.quantity} {item.unit} ({item.category}){price_str}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")


def print_usage_examples():
    """Print code usage examples"""
    print()
    print("=" * 80)
    print("USAGE EXAMPLES")
    print("=" * 80)
    print()
    
    print("1. Scan receipt from file:")
    print("-" * 80)
    print("""
from services.receipt_scanner import receipt_scanner_service

# Scan receipt
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Access items
for item in result.items:
    print(f"{item.name}: {item.quantity} {item.unit} - {item.category}")
    if item.price:
        print(f"  Price: ${item.price:.2f}")
""")
    
    print()
    print("2. Scan receipt from base64:")
    print("-" * 80)
    print("""
import base64
from services.receipt_scanner import receipt_scanner_service

# Read and encode image
with open('receipt.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# Scan receipt
result = await receipt_scanner_service.scan_receipt(image_data)

# Access results
print(f"Store: {result.store_name}")
print(f"Date: {result.receipt_date}")
print(f"Total: ${result.total_amount}")
print(f"Items: {result.total_items}")
""")
    
    print()
    print("3. Group items by category:")
    print("-" * 80)
    print("""
# Scan receipt
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Group by category
grouped = receipt_scanner_service.group_items_by_category(result.items)

for category, items in grouped.items():
    print(f"{category}:")
    for item in items:
        print(f"  - {item.name}")
""")
    
    print()
    print("4. Calculate spending by category:")
    print("-" * 80)
    print("""
# Scan receipt
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Calculate totals
totals = receipt_scanner_service.calculate_category_totals(result.items)

for category, total in sorted(totals.items(), key=lambda x: x[1], reverse=True):
    print(f"{category}: ${total:.2f}")
""")
    
    print()
    print("5. Format for grocery list:")
    print("-" * 80)
    print("""
# Scan receipt
result = await receipt_scanner_service.scan_receipt_from_file('receipt.jpg')

# Format items for database insertion
formatted_items = receipt_scanner_service.format_items_for_grocery_list(result.items)

# Add to grocery list or pantry
for item in formatted_items:
    # Insert into database
    # db.add(GroceryItem(**item))
    pass
""")
    print()


async def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Receipt Scanner Test Script")
        print()
        print("Usage:")
        print("  python test_receipt_scanner.py <path_to_receipt_image>")
        print()
        print("Example:")
        print("  python test_receipt_scanner.py ~/Downloads/grocery_receipt.jpg")
        print()
        print("Supported formats: JPG, JPEG, PNG")
        print()
        print_usage_examples()
        return
    
    image_path = sys.argv[1]
    
    # Run the test
    await test_scan_receipt_from_file(image_path)
    
    # Print usage examples
    print_usage_examples()
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print("✅ Receipt scanning extracts:")
    print("   - Item names")
    print("   - Quantities")
    print("   - Units (lb, oz, gallon, each, etc.)")
    print("   - Categories (Produce, Dairy, Meat, etc.)")
    print("   - Prices (if visible)")
    print("   - Store name and date")
    print()
    print("🔧 Integration ready for:")
    print("   - Automatic pantry updates")
    print("   - Grocery list generation")
    print("   - Spending tracking")
    print("   - Shopping analytics")
    print()


if __name__ == "__main__":
    asyncio.run(main())
