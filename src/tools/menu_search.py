"""
Menu Search Tool - Phase 2
Enhanced with vector search (semantic) + keyword search (hybrid)
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
    
    async def execute(self, query: str, category: str = None, use_semantic: bool = True) -> ToolResult:
        """Search menu using keyword + semantic search"""
        try:
            # First try keyword search
            keyword_results = self._keyword_search(query, category)
            
            # If semantic search enabled and Qdrant available, try that too
            semantic_results = []
            if use_semantic:
                try:
                    from src.vector_db.qdrant_client import QdrantManager
                    qdrant = QdrantManager()
                    semantic_results = await qdrant.search(query, limit=5)
                except Exception as e:
                    print(f"[MenuSearch] Semantic search unavailable: {e}")
            
            # Combine and deduplicate results
            all_results = self._merge_results(keyword_results, semantic_results)
            
            # Add explanation
            explanation = self._generate_explanation(query, all_results)
            
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "category_filter": category,
                    "results": all_results[:5],
                    "count": len(all_results),
                    "explanation": explanation,
                    "used_semantic": len(semantic_results) > 0
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Menu search failed: {str(e)}"
            )
    
    def _keyword_search(self, query: str, category: str = None) -> list:
        """Traditional keyword search"""
        menu = self._load_menu()
        query_lower = query.lower()
        results = []
        
        for cat, items in menu.items():
            if category and cat != category:
                continue
            
            if isinstance(items, list):
                for item in items:
                    item_str = json.dumps(item).lower()
                    if query_lower in item_str:
                        results.append({
                            "category": cat,
                            "match_type": "keyword",
                            **item
                        })
        
        return results
    
    def _merge_results(self, keyword_results: list, semantic_results: list) -> list:
        """Merge and deduplicate results from both methods"""
        seen = set()
        merged = []
        
        # Add semantic results first (higher priority)
        for item in semantic_results:
            name = item.get("name")
            if name and name not in seen:
                seen.add(name)
                merged.append({
                    "name": name,
                    "category": item.get("category"),
                    "price": item.get("price"),
                    "description": item.get("description"),
                    "match_type": "semantic",
                    "score": item.get("score", 0)
                })
        
        # Add keyword results
        for item in keyword_results:
            name = item.get("name")
            if name and name not in seen:
                seen.add(name)
                merged.append(item)
        
        return merged
    
    def _generate_explanation(self, query: str, results: list) -> str:
        """Generate human-friendly explanation of results"""
        if not results:
            return f"I couldn't find anything matching '{query}'. Try 'wings', 'sides', or 'drinks'."
        
        # Detect query intent
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["spicy", "hot", "mild"]):
            return f"Here are some options based on your preference for '{query}':"
        
        if any(word in query_lower for word in ["boneless", "bone-in", "classic"]):
            return f"Here are the wing styles you're looking for:"
        
        if any(word in query_lower for word in ["cheap", "deal", "combo", "value"]):
            return f"Great choice! Here are some value options:"
        
        return f"Here are our {results[0].get('category', 'items')} that match '{query}':"
