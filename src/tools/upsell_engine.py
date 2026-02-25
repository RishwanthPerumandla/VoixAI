"""
Upsell Engine Tool
Suggests add-ons and upgrades to increase order value
"""

from typing import Dict, List, Any
from src.tools.base import BaseTool, ToolResult


class UpsellEngineTool(BaseTool):
    """Generate smart upsell suggestions"""
    
    name = "suggest_upsell"
    description = "Suggest relevant add-ons, upgrades, or combos based on current order items"
    parameters = {
        "type": "object",
        "properties": {
            "current_items": {
                "type": "array",
                "description": "Current items in the order",
                "items": {"type": "object"}
            },
            "customer_history": {
                "type": "object",
                "description": "Previous orders/preferences if available"
            }
        },
        "required": ["current_items"]
    }
    
    def __init__(self):
        super().__init__()
        self.upsell_rules = [
            {
                "name": "Wings need dips",
                "condition": lambda items: any("wing" in i.get("name", "").lower() for i in items),
                "suggestion": "Add our famous Ranch or Blue Cheese dip for just $0.99?",
                "items": [
                    {"name": "Ranch Dip", "price": 0.99},
                    {"name": "Blue Cheese Dip", "price": 0.99}
                ],
                "max_suggestions": 1
            },
            {
                "name": "Large order needs drink",
                "condition": lambda items: sum(i.get("quantity", 0) for i in items) >= 10 and 
                                          not any("drink" in i.get("name", "").lower() or 
                                                 i.get("category") == "drinks" for i in items),
                "suggestion": "Add a refreshing drink? Our 32oz sodas are only $2.99",
                "items": [
                    {"name": "32oz Coca-Cola", "price": 2.99},
                    {"name": "32oz Sprite", "price": 2.99}
                ],
                "max_suggestions": 1
            },
            {
                "name": "Combo upgrade",
                "condition": lambda items: any("wing" in i.get("name", "").lower() for i in items) and
                                          len(items) < 3,
                "suggestion": "Make it a combo! Add fries and a drink and save $2",
                "items": [
                    {"name": "Combo Upgrade (fries + drink)", "price": 4.99, "savings": 2.00}
                ],
                "max_suggestions": 1
            },
            {
                "name": "Side suggestion",
                "condition": lambda items: any("wing" in i.get("name", "").lower() for i in items) and
                                          not any("fries" in i.get("name", "").lower() or 
                                                 "side" in i.get("category", "") for i in items),
                "suggestion": "Our Seasoned Fries go great with wings! Only $3.99",
                "items": [
                    {"name": "Seasoned Fries", "price": 3.99}
                ],
                "max_suggestions": 1
            },
            {
                "name": "Dessert suggestion",
                "condition": lambda items: sum(i.get("quantity", 0) for i in items) >= 15,
                "suggestion": "Save room for dessert? Our Triple Chocolate Brownie is $4.99",
                "items": [
                    {"name": "Triple Chocolate Brownie", "price": 4.99}
                ],
                "max_suggestions": 1
            }
        ]
    
    async def execute(
        self,
        current_items: List[Dict],
        customer_history: Dict = None
    ) -> ToolResult:
        """Generate upsell suggestions"""
        try:
            if not current_items:
                return ToolResult(
                    success=True,
                    data={
                        "suggestions": [],
                        "message": "No items in order yet"
                    }
                )
            
            suggestions = []
            suggested_count = 0
            max_total_suggestions = 2  # Max 2 suggestions per order
            
            for rule in self.upsell_rules:
                if suggested_count >= max_total_suggestions:
                    break
                
                if rule["condition"](current_items):
                    # Check if already suggested item is in order
                    already_has = False
                    for suggested_item in rule["items"]:
                        for order_item in current_items:
                            if suggested_item["name"].lower() in order_item.get("name", "").lower():
                                already_has = True
                                break
                    
                    if not already_has:
                        suggestions.append({
                            "rule_name": rule["name"],
                            "suggestion_text": rule["suggestion"],
                            "items": rule["items"],
                            "max_suggestions": rule.get("max_suggestions", 1)
                        })
                        suggested_count += 1
            
            # Pick the best suggestion
            best_suggestion = None
            if suggestions:
                # Prioritize combo upgrades, then dips, then others
                priority_order = ["Combo upgrade", "Wings need dips", "Side suggestion", 
                                "Large order needs drink", "Dessert suggestion"]
                
                for priority in priority_order:
                    for s in suggestions:
                        if s["rule_name"] == priority:
                            best_suggestion = s
                            break
                    if best_suggestion:
                        break
                
                if not best_suggestion:
                    best_suggestion = suggestions[0]
            
            return ToolResult(
                success=True,
                data={
                    "has_suggestion": best_suggestion is not None,
                    "suggestion": best_suggestion,
                    "all_suggestions": suggestions,
                    "message": best_suggestion["suggestion_text"] if best_suggestion else None
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Upsell generation failed: {str(e)}")
