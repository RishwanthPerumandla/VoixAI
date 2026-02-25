"""
Menu Search Tool - Phase 1.6 (Basic)
Simple keyword-based menu search for initial implementation
Will be enhanced with vector search in Phase 2
"""

import json
from pathlib import Path
from typing import Any, Dict
from src.tools.base import BaseTool, ToolResult


class MenuSearchTool(BaseTool):
    """Search menu items by keyword"""
    
    name = "search_menu"
    description = "Search menu items by name, category, or description. Returns matching items with prices and details."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for menu items (e.g., 'wings', 'spicy', 'boneless')"
            },
            "category": {
                "type": "string",
                "enum": ["wings", "sides", "drinks", "dips", "combos"],
                "description": "Optional category filter"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, menu_path: str = "data/menu.json"):
        super().__init__()
        self.menu_path = Path(menu_path)
        self._menu_cache = None
    
    def _load_menu(self) -> Dict:
        """Load menu from JSON file"""
        if self._menu_cache is not None:
            return self._menu_cache
        
        try:
            with open(self.menu_path, 'r') as f:
                self._menu_cache = json.load(f)
            return self._menu_cache
        except FileNotFoundError:
            # Return default menu if file doesn't exist
            return self._get_default_menu()
    
    def _get_default_menu(self) -> Dict:
        """Default menu for testing"""
        return {
            "wings": [
                {"name": "Classic Bone-In Wings", "price": 12.99, "sizes": [8, 10, 15], "description": "Traditional bone-in chicken wings"},
                {"name": "Boneless Wings", "price": 11.99, "sizes": [8, 10, 15], "description": "Breaded boneless chicken wings"},
            ],
            "flavors": [
                {"name": "Lemon Pepper", "spiciness": "mild"},
                {"name": "Buffalo", "spiciness": "medium"},
                {"name": "Mango Habanero", "spiciness": "hot"},
                {"name": "Garlic Parmesan", "spiciness": "mild"},
            ],
            "sides": [
                {"name": "Seasoned Fries", "price": 3.99},
                {"name": "Veggie Sticks", "price": 2.99},
            ],
            "drinks": [
                {"name": "Coca-Cola", "price": 2.99, "sizes": ["20oz", "32oz"]},
                {"name": "Sprite", "price": 2.99, "sizes": ["20oz", "32oz"]},
            ],
            "dips": [
                {"name": "Ranch", "price": 0.99},
                {"name": "Blue Cheese", "price": 0.99},
                {"name": "Honey Mustard", "price": 0.99},
            ]
        }
    
    async def execute(self, query: str, category: str = None) -> ToolResult:
        """Search menu by keyword"""
        try:
            menu = self._load_menu()
            query_lower = query.lower()
            results = []
            
            # Search through all categories
            for cat, items in menu.items():
                if category and cat != category:
                    continue
                
                if isinstance(items, list):
                    for item in items:
                        item_str = json.dumps(item).lower()
                        if query_lower in item_str:
                            results.append({
                                "category": cat,
                                **item
                            })
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "category_filter": category,
                    "results": results[:5],  # Limit to top 5
                    "count": len(results)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Menu search failed: {str(e)}"
            )
