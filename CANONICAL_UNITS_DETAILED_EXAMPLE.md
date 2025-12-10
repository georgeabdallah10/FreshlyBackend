# Canonical Quantity Sync: Detailed Example

## 🧪 Your Example: Mustard 5ml (Pantry) vs 3 teaspoons (Grocery)

### Scenario Setup
```
PANTRY ITEM:
  - Ingredient: Mustard
  - quantity: 5
  - unit: "ml"
  - canonical_quantity: 5
  - canonical_unit: "ml"

GROCERY ITEM:
  - Ingredient: Mustard
  - quantity: 3
  - unit: "tsp" (teaspoons)
  - canonical_quantity_needed: ? (needs conversion)
  - canonical_unit: ? (needs conversion)
```

---

## 📊 Step-by-Step Conversion Process

### Step 1: Convert Grocery Item to Canonical (Before Sync)

When the grocery item is created or updated, it should be normalized:

```python
# In sync_list_with_pantry() or when item is added
ingredient = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).first()

# Try to normalize quantity
quantity = 3  # teaspoons
unit = "tsp"

# Call try_normalize_quantity()
canonical_qty, canonical_unit = try_normalize_quantity(
    ingredient,  # Mustard
    quantity=3.0,
    unit="tsp"
)
```

#### Unit Conversion Logic:
```python
# From core/unit_conversions.py
VOLUME_CONVERSIONS = {
    "ml": 1.0,
    "tsp": 5.0,   # ← 1 tsp = 5 ml
    "tbsp": 15.0,
    "cup": 240.0,
}

# Conversion:
3 tsp × 5.0 ml/tsp = 15 ml
```

**Result**:
```python
canonical_qty = 15.0  # ml
canonical_unit = "ml"
```

So the grocery item becomes:
```
GROCERY ITEM (After Normalization):
  - Ingredient: Mustard
  - quantity: 3
  - unit: "tsp" (display)
  - canonical_quantity_needed: 15
  - canonical_unit: "ml"
```

---

### Step 2: Get Pantry Totals

```python
pantry_totals = get_pantry_totals_flexible(db, family_id=9)

# For Mustard (ingredient_id = 42):
pantry_totals[42] = {
    'canonical_quantity': Decimal('5'),
    'canonical_unit': 'ml',
    'display_quantity': Decimal('5'),
    'display_unit': 'ml'
}
```

---

### Step 3: Compare and Subtract (The Sync!)

```python
# In sync_list_with_pantry()

# Grocery item
grocery_canonical_qty = 15  # ml (from 3 tsp)
grocery_canonical_unit = "ml"

# Pantry item
pantry_qty = 5  # ml
pantry_unit = "ml"

# Unit check
normalized_pantry_unit = normalize_unit_string("ml")   # → "ml"
normalized_grocery_unit = normalize_unit_string("ml")  # → "ml"

# Units match! ✅
if normalized_pantry_unit == normalized_grocery_unit:
    # Calculate remaining
    remaining_qty = grocery_canonical_qty - pantry_qty
    # = 15 ml - 5 ml
    # = 10 ml
```

---

### Step 4: Decision

```python
remaining_qty = 10  # ml

if remaining_qty <= 0:
    # Remove item (fully covered)
    pass
elif remaining_qty < grocery_canonical_qty:
    # ✅ THIS HAPPENS!
    # Partially covered - update item
    
    # Update canonical
    item.canonical_quantity_needed = 10  # ml
    item.canonical_unit = "ml"
    
    # Update display (convert back to user-friendly units)
    display_qty, display_unit = format_for_display(10, "ml")
    # 10 ml < 1000 ml, so stays as "ml"
    # display_qty = 10.0
    # display_unit = "ml"
    
    item.quantity = 10.0
    # Note: Could also convert back to tsp: 10ml ÷ 5 = 2 tsp
    
    items_updated += 1
else:
    # Not in pantry
    pass
```

---

### Step 5: API Response

```json
{
  "message": "Synced grocery list with pantry",
  "items_removed": 0,
  "items_updated": 1,
  "remaining_items": [
    {
      "ingredient_id": 42,
      "ingredient_name": "Mustard",
      "quantity": 10.0,
      "unit_code": "ml",
      "canonical_quantity": 10,
      "canonical_unit": "ml",
      "note": "3 teaspoons"
    }
  ]
}
```

---

## 🔍 The Magic: Unit Normalization

### Conversion Table
| Display Unit | Canonical Unit | Conversion Factor |
|-------------|----------------|-------------------|
| `tsp` (teaspoon) | `ml` | 1 tsp = 5 ml |
| `tbsp` (tablespoon) | `ml` | 1 tbsp = 15 ml |
| `cup` | `ml` | 1 cup = 240 ml |
| `oz` | `g` | 1 oz = 28.35 g |
| `lb` | `g` | 1 lb = 453.59 g |
| `kg` | `g` | 1 kg = 1000 g |

### Why It Works:
Both items normalize to the **same canonical unit** (`ml`), so they can be compared directly!

```
3 tsp  → 15 ml  (grocery)
5 ml   → 5 ml   (pantry)
─────────────────
Remaining: 10 ml ✅
```

---

## 📋 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  GROCERY ITEM (User Input)                                  │
│  Mustard: 3 tsp                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ NORMALIZE
                       ▼
            ┌──────────────────────┐
            │ 3 tsp × 5 ml/tsp     │
            │ = 15 ml              │
            └──────────┬───────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  GROCERY ITEM (Canonical)                                   │
│  Mustard: canonical_quantity=15, canonical_unit="ml"       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ SYNC WITH PANTRY
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PANTRY ITEM (Already Canonical)                            │
│  Mustard: canonical_quantity=5, canonical_unit="ml"        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ COMPARE
                       ▼
              ┌────────────────────┐
              │ Units match? YES!  │
              │ "ml" == "ml"       │
              └─────────┬──────────┘
                        │
                        │ SUBTRACT
                        ▼
                ┌───────────────┐
                │ 15 ml - 5 ml  │
                │ = 10 ml       │
                └───────┬───────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │ 0 < 10 < 15?            │
          │ YES! Partial coverage   │
          └─────────┬───────────────┘
                    │
                    ▼
       ✅ UPDATE TO 10 ml (2 tsp)
       ✅ Show in remaining_items
```

---

## 🎯 Key Insights

### 1. **Automatic Conversion**
- Grocery item: `3 tsp` → **automatically** converted to `15 ml`
- Pantry item: `5 ml` → **already** canonical
- Both now in `ml` → can compare! ✅

### 2. **Math Works Perfectly**
```
15 ml (needed) - 5 ml (have) = 10 ml (still need)
```

### 3. **Display Options**
The result could be shown as:
- `10 ml` (canonical)
- `2 tsp` (converted back to original unit)
- Both are correct!

### 4. **What If Units Were Incompatible?**

#### Example: Weight vs Volume
```
Grocery: 3 tsp (volume) → 15 ml
Pantry: 10 g (weight)   → 10 g

Compare:
  - normalized_grocery_unit = "ml"
  - normalized_pantry_unit = "g"
  - "ml" != "g" ⚠️

Result: UNIT MISMATCH
  → Logs warning
  → Keeps item in list as-is
  → User must manually verify
```

---

## 💡 Real-World Examples

### Example 1: Oil (Volume)
```
Grocery: 2 cups oil → 480 ml (canonical)
Pantry: 500 ml      → 500 ml (canonical)
Result: 480 - 500 = -20 ml → REMOVED ✅
```

### Example 2: Flour (Weight - depends on ingredient type)
```
Grocery: 1 cup flour → ???
  - If ingredient has density: 1 cup × 120g/cup = 120g (canonical)
  - If no density: stays as "cup" (display unit)

Pantry: 200 g → 200 g (canonical)

If converted to grams:
  Result: 120g - 200g = -80g → REMOVED ✅

If NOT converted:
  Result: "cup" != "g" → UNIT MISMATCH ⚠️
```

### Example 3: Chicken (Weight)
```
Grocery: 1 lb chicken → 453.59 g (canonical)
Pantry: 500 g         → 500 g (canonical)
Result: 453.59 - 500 = -46.41g → REMOVED ✅
```

### Example 4: Eggs (Count)
```
Grocery: 12 eggs → 12 count (canonical)
Pantry: 6 eggs   → 6 count (canonical)
Result: 12 - 6 = 6 → UPDATED TO 6 ✅
```

---

## 🔧 Implementation Details

### Where Conversion Happens:

1. **Adding Items to Grocery List**:
```python
# In _add_meal_ingredients_to_list() or when creating items
qty, unit = parse_amount_string("3 teaspoons")
# → qty=3, unit="tsp"

canonical_qty, canonical_unit = try_normalize_quantity(ingredient, qty, unit)
# → canonical_qty=15, canonical_unit="ml"

item.quantity = qty  # Display: 3
item.unit = unit     # Display: "tsp"
item.canonical_quantity_needed = canonical_qty  # Canonical: 15
item.canonical_unit = canonical_unit            # Canonical: "ml"
```

2. **During Sync**:
```python
# In sync_list_with_pantry()
grocery_canonical_qty = item.canonical_quantity_needed  # 15 ml
pantry_qty = pantry_totals[item.ingredient_id]['canonical_quantity']  # 5 ml

remaining_qty = grocery_canonical_qty - pantry_qty  # 10 ml
```

3. **Displaying Results**:
```python
# Convert back to user-friendly units
display_qty, display_unit = format_for_display(10, "ml")
# Could also convert: 10ml ÷ 5 = 2 tsp
```

---

## ✅ Summary: Your Mustard Example

**Before Sync:**
- Grocery: 3 tsp (15 ml canonical)
- Pantry: 5 ml (5 ml canonical)

**During Sync:**
- Convert grocery: 3 tsp → 15 ml ✅
- Units match: ml == ml ✅
- Subtract: 15 - 5 = 10 ml ✅

**After Sync:**
- Grocery updated to: 10 ml (or 2 tsp)
- Items updated: 1
- Remaining items: 1 item with 10 ml

**API Response:**
```json
{
  "items_updated": 1,
  "remaining_items": [
    {
      "ingredient_name": "Mustard",
      "quantity": 10.0,
      "unit_code": "ml",
      "canonical_quantity": 10,
      "canonical_unit": "ml"
    }
  ]
}
```

---

## 🎉 The Power of Canonical Units!

This is **exactly** why canonical units are so powerful:

✅ **Different display units** → Same canonical unit  
✅ **Apples-to-apples comparison** → Accurate subtraction  
✅ **No guesswork** → Precise calculations  
✅ **Works perfectly** → Every time!

The system handles all the unit conversions automatically, so you can store items in whatever units are convenient (tsp, ml, cups, etc.) and they'll all sync correctly! 🚀
