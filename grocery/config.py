"""Constants and paths for the grocery CLI."""

import os
from dotenv import load_dotenv

load_dotenv()

TASK_LIST_ID = os.getenv("GROCERY_TASK_LIST_ID")
PARENT_TASK_ID = os.getenv("GROCERY_PARENT_TASK_ID")
CATALOG_PATH = os.getenv("CATALOG_PATH", "./data/catalog.json")
STORE_ID = os.getenv("KROGER_STORE_ID", "70100123")
DIVISION = os.getenv("KROGER_DIVISION", "620")
KROGER_CLIENT_ID = os.getenv("KROGER_CLIENT_ID")
TOKEN_DIR = os.getenv("TOKEN_DIR", ".")

# Store-order categories for aisle sorting
STORE_ORDER = [
    ("Produce", ["fruit", "vegetable", "banana", "apple", "berry", "berries", "lettuce", "tomato",
                  "onion", "potato", "pepper", "carrot", "celery", "broccoli", "avocado", "lemon",
                  "lime", "orange", "grape", "mango", "pear", "peach", "plum", "melon", "corn",
                  "cucumber", "spinach", "kale", "herb", "cilantro", "parsley", "basil", "mint",
                  "garlic", "ginger", "mushroom", "zucchini", "squash", "cabbage", "radish",
                  "flower", "bouquet", "roses", "blackberry", "blackberries", "strawberry",
                  "strawberries", "blueberry", "blueberries", "raspberry", "raspberries",
                  "pineapple", "watermelon", "cantaloupe", "honeydew", "kiwi", "pomegranate",
                  "asparagus", "artichoke", "beet", "turnip", "sweet potato", "green bean",
                  "snap pea", "pea", "fresh"]),
    ("Bakery/Deli", ["bread", "bagel", "muffin", "croissant", "roll", "bun", "tortilla", "wrap",
                      "pita", "deli", "rotisserie", "bakery", "cake", "donut", "pastry", "pie crust"]),
    ("Dairy/Eggs", ["milk", "cheese", "yogurt", "butter", "cream", "egg", "eggs", "sour cream",
                     "cottage cheese", "cream cheese", "half and half", "whipped", "creamer",
                     "oat milk", "almond milk", "string cheese", "shredded cheese"]),
    ("Meat/Seafood", ["chicken", "beef", "pork", "steak", "ground", "turkey", "bacon", "sausage",
                       "ham", "salami", "pepperoni", "fish", "salmon", "shrimp", "tuna", "crab",
                       "lobster", "meat", "ribs", "brisket", "roast", "lamb", "lunch meat",
                       "hot dog", "bratwurst"]),
    ("Frozen", ["frozen", "ice cream", "pizza", "popsicle", "waffle", "freezer", "frozen vegetable",
                "frozen fruit", "tv dinner", "lean cuisine", "hot pocket"]),
    ("Snacks/Nuts", ["chip", "chips", "cracker", "pretzel", "popcorn", "nut", "nuts", "peanut",
                      "almond", "cashew", "walnut", "pistachio", "trail mix", "granola bar",
                      "snack", "jerky", "goldfish", "cheez-it", "tortilla chip"]),
    ("Condiments/Oils/Sauces", ["ketchup", "mustard", "mayo", "mayonnaise", "sauce", "salsa",
                                  "dressing", "oil", "olive oil", "vinegar", "soy sauce",
                                  "hot sauce", "sriracha", "bbq", "marinade", "relish",
                                  "worcestershire", "chili oil", "ranch", "honey"]),
    ("Canned/Dry Goods", ["can", "canned", "soup", "bean", "beans", "rice", "pasta", "noodle",
                           "cereal", "oatmeal", "broth", "stock", "tomato sauce", "tomato paste",
                           "tuna can", "chickpea", "lentil", "quinoa", "couscous", "mac and cheese",
                           "ramen", "peanut butter", "jelly", "jam"]),
    ("Baking/Candy", ["sugar", "flour", "baking", "vanilla", "chocolate", "candy", "cocoa",
                       "baking powder", "baking soda", "yeast", "sprinkles", "frosting",
                       "cake mix", "brownie", "cookie", "gummy", "turtle", "dipping chocolate",
                       "confection"]),
    ("Beverages", ["water", "juice", "soda", "coffee", "tea", "beer", "wine", "sparkling",
                    "gatorade", "energy drink", "kombucha", "lemonade", "coke", "pepsi",
                    "la croix", "lacroix", "drink", "beverage", "monster", "red bull"]),
    ("Household/Cleaning", ["paper towel", "toilet paper", "trash bag", "detergent", "soap",
                             "dish soap", "sponge", "cleaner", "bleach", "wipe", "wipes",
                             "aluminum foil", "plastic wrap", "ziploc", "bag", "tide",
                             "laundry", "fabric softener", "dryer sheet"]),
    ("Personal Care", ["shampoo", "conditioner", "body wash", "lotion", "deodorant", "toothpaste",
                        "toothbrush", "razor", "floss", "sunscreen", "bandaid", "medicine",
                        "vitamin", "supplement", "tylenol", "ibuprofen", "allergy"]),
]


def get_aisle_index(item_name: str) -> int:
    """Return the store-order index for an item name (lower = earlier in store)."""
    name_lower = item_name.lower()
    for i, (category, keywords) in enumerate(STORE_ORDER):
        for kw in keywords:
            if kw in name_lower:
                return i
    return len(STORE_ORDER)  # Unknown → end of list
