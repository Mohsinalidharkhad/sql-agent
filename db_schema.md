# Restaurant Database Schema

## Core Tables

### 1. dishes
Primary key: `dish_id` (integer, auto-increment)
- `name` (varchar, required): Name of the dish (e.g., Paneer Tikka, Paneer Butter Masala, Dal Makhani, Tandoori Roti)
- `category` (varchar, required): Category of the dish (e.g., Main Course, Appetizer, Dessert)
- `description` (text): Detailed description of the dish (e.g., Grilled paneer cubes marinated in spiced yogurt, served with mint chutney)
- `base_price` (numeric, required): Base price of the dish (e.g., 200.00, 350.00, 300.00)
- `is_vegetarian` (boolean, default false): Whether the dish is vegetarian
- `is_vegan` (boolean, default false): Whether the dish is vegan
- `spicy_level` (varchar): Spiciness level of the dish (e.g., None, Mild, Medium, Hot)
- `cuisine` (varchar): Type of cuisine (e.g., Punjabi, Mughlai, Fusion)

### 2. dish_variants
Primary key: `variant_id` (integer, auto-increment)
Foreign key: `dish_id` references dishes(dish_id)
- `variant_name` (varchar, required): Name of the variant (e.g., Half Plate, Full Plate, Regular)
- `price` (numeric, required): Price of this specific variant (e.g., 200.00, 350.00, 300.00)

### 3. ingredients
Primary key: `ingredient_id` (integer, auto-increment)
Foreign key: `dish_id` references dishes(dish_id)
- `ingredient_name` (varchar, required): Name of the ingredient (e.g., Paneer, Yogurt, Capsicum, Tomato)
- `is_allergen` (boolean, default false): Whether the ingredient is a common allergen

### 4. item_modifiers
Primary key: `modifier_id` (integer, auto-increment)
Foreign key: `dish_id` references dishes(dish_id)
- `modifier_name` (varchar, required): Name of the modifier (e.g., Extra Mint Chuttney, Extra Milk, Less Spicy)
- `modifier_type` (varchar): Type of modification (e.g., Sauce, Add-on, Spice adjstment, Jain preparation)
- `additional_price` (numeric, default 0.00): Additional cost for this modifier (e.g., 30.00, 20.00, 60.00)

## Relationships

1. A dish can have:
   - Multiple variants (one-to-many with dish_variants)
   - Multiple ingredients (one-to-many with ingredients)
   - Multiple modifiers (one-to-many with item_modifiers)

2. Each variant, ingredient, and modifier belongs to exactly one dish (many-to-one with dishes)

# Synonym words
- Bread: Rotis, kulcha, naan, paav, roti
- Dessert: Meetha, Sweet, Sweet dish, halwa
- Beverage: Cold drink
- Appetizer: starter