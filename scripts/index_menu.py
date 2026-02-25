"""
Script to index menu items into Qdrant for semantic search
Run this once to set up vector search
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vector_db.qdrant_client import QdrantManager


async def main():
    """Index menu items into Qdrant"""
    print("="*60)
    print("Indexing Menu Items to Qdrant")
    print("="*60)
    
    # Load menu
    menu_path = Path("data/menu.json")
    if not menu_path.exists():
        print("Creating default menu...")
        menu = create_default_menu()
        menu_path.parent.mkdir(parents=True, exist_ok=True)
        with open(menu_path, 'w') as f:
            json.dump(menu, f, indent=2)
    else:
        with open(menu_path, 'r') as f:
            menu = json.load(f)
    
    # Flatten menu items
    menu_items = []
    for category, items in menu.items():
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    item["category"] = category
                    menu_items.append(item)
    
    print(f"Found {len(menu_items)} menu items")
    
    # Initialize Qdrant
    qdrant = QdrantManager()
    
    # Create collection
    success = await qdrant.init_collection()
    if not success:
        print("[ERROR] Failed to initialize Qdrant collection")
        return
    
    # Index items
    success = await qdrant.index_menu_items(menu_items)
    if success:
        print("[SUCCESS] Menu items indexed successfully!")
        
        # Test search
        print("\nTesting search...")
        results = await qdrant.search("spicy wings", limit=3)
        print(f"Query: 'spicy wings'")
        for r in results:
            print(f"  - {r['name']} (score: {r['score']:.3f})")
    else:
        print("[ERROR] Failed to index menu items")


def create_default_menu():
    """Create default Wingstop menu"""
    return {
        "wings": [
            {
                "name": "Classic Bone-In Wings",
                "description": "Traditional bone-in chicken wings, crispy and juicy",
                "price": 12.99,
                "sizes": [8, 10, 15],
                "category": "wings"
            },
            {
                "name": "Boneless Wings",
                "description": "Breaded boneless chicken wings, tender and delicious",
                "price": 11.99,
                "sizes": [8, 10, 15],
                "category": "wings"
            }
        ],
        "flavors": [
            {"name": "Lemon Pepper", "spiciness": "mild", "description": "Zesty lemon with cracked black pepper"},
            {"name": "Buffalo", "spiciness": "medium", "description": "Classic hot sauce with buttery finish"},
            {"name": "Mango Habanero", "spiciness": "hot", "description": "Sweet mango with fiery habanero kick"},
            {"name": "Garlic Parmesan", "spiciness": "mild", "description": "Roasted garlic with parmesan cheese"},
            {"name": "Atomic", "spiciness": "extreme", "description": "Our hottest flavor - not for the faint of heart"},
            {"name": "Hickory Smoked BBQ", "spiciness": "mild", "description": "Sweet and smoky BBQ sauce"}
        ],
        "sides": [
            {"name": "Seasoned Fries", "price": 3.99, "description": "Crispy fries with our signature seasoning"},
            {"name": "Cheese Fries", "price": 4.99, "description": "Seasoned fries topped with melted cheese"},
            {"name": "Veggie Sticks", "price": 2.99, "description": "Fresh celery and carrot sticks"}
        ],
        "drinks": [
            {"name": "Coca-Cola", "price": 2.99, "sizes": ["20oz", "32oz"]},
            {"name": "Sprite", "price": 2.99, "sizes": ["20oz", "32oz"]},
            {"name": "Dr Pepper", "price": 2.99, "sizes": ["20oz", "32oz"]},
            {"name": "Bottled Water", "price": 1.99}
        ],
        "dips": [
            {"name": "Ranch Dip", "price": 0.99, "description": "Creamy ranch dressing"},
            {"name": "Blue Cheese Dip", "price": 0.99, "description": "Tangy blue cheese dressing"},
            {"name": "Honey Mustard", "price": 0.99, "description": "Sweet and tangy honey mustard"}
        ],
        "desserts": [
            {"name": "Triple Chocolate Brownie", "price": 4.99, "description": "Rich chocolate brownie with chunks"},
            {"name": "Churros", "price": 3.99, "description": "Cinnamon sugar churros with chocolate dip"}
        ]
    }


if __name__ == "__main__":
    asyncio.run(main())
