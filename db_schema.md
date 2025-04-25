# Restaurant Bot Database Schema

## Core Tables

### 1. dishes
Primary key: `dish_id` (integer, auto-increment)
- `name` (varchar, required): Name of the dish
- `category` (varchar, required): Category of the dish (e.g., Main Course, Appetizer, Dessert)
- `description` (text): Detailed description of the dish
- `base_price` (numeric, required): Base price of the dish
- `is_vegetarian` (boolean, default false): Whether the dish is vegetarian
- `is_vegan` (boolean, default false): Whether the dish is vegan
- `spicy_level` (varchar): Spiciness level of the dish (e.g., None, Mild, Hot)
- `cuisine` (varchar): Type of cuisine (e.g., Italian, Thai, American)

### 2. dish_variants
Primary key: `variant_id` (integer, auto-increment)
Foreign key: `dish_id` references dishes(dish_id)
- `variant_name` (varchar, required): Name of the variant
- `price` (numeric, required): Price of this specific variant

### 3. ingredients
Primary key: `ingredient_id` (integer, auto-increment)
Foreign key: `dish_id` references dishes(dish_id)
- `ingredient_name` (varchar, required): Name of the ingredient
- `is_allergen` (boolean, default false): Whether the ingredient is a common allergen

### 4. item_modifiers
Primary key: `modifier_id` (integer, auto-increment)
Foreign key: `dish_id` references dishes(dish_id)
- `modifier_name` (varchar, required): Name of the modifier
- `modifier_type` (varchar): Type of modification
- `additional_price` (numeric, default 0.00): Additional cost for this modifier

## Relationships

1. A dish can have:
   - Multiple variants (one-to-many with dish_variants)
   - Multiple ingredients (one-to-many with ingredients)
   - Multiple modifiers (one-to-many with item_modifiers)

2. Each variant, ingredient, and modifier belongs to exactly one dish (many-to-one with dishes)

## Common Queries

1. Get all dishes with their basic information:
```sql
SELECT * FROM dishes;
```

2. Get vegetarian dishes:
```sql
SELECT * FROM dishes WHERE is_vegetarian = true;
```

3. Get dishes by category:
```sql
SELECT * FROM dishes WHERE category = 'Main Course';
```

4. Get dishes with their variants:
```sql
SELECT d.*, dv.variant_name, dv.price 
FROM dishes d 
LEFT JOIN dish_variants dv ON d.dish_id = dv.dish_id;
```

5. Get dishes with their ingredients:
```sql
SELECT d.*, i.ingredient_name, i.is_allergen 
FROM dishes d 
LEFT JOIN ingredients i ON d.dish_id = i.dish_id;
```

6. Get dishes with their modifiers:
```sql
SELECT d.*, m.modifier_name, m.modifier_type, m.additional_price 
FROM dishes d 
LEFT JOIN item_modifiers m ON d.dish_id = m.dish_id;
```

7. Get complete dish information:
```sql
SELECT 
    d.*,
    array_agg(DISTINCT dv.variant_name) as variants,
    array_agg(DISTINCT i.ingredient_name) as ingredients,
    array_agg(DISTINCT m.modifier_name) as modifiers
FROM dishes d
LEFT JOIN dish_variants dv ON d.dish_id = dv.dish_id
LEFT JOIN ingredients i ON d.dish_id = i.dish_id
LEFT JOIN item_modifiers m ON d.dish_id = m.dish_id
GROUP BY d.dish_id;
``` 