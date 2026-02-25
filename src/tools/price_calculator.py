"""
Price Calculator Tool
Calculates order totals with tax, combos, and discounts
"""

from typing import Dict, List, Any
from src.tools.base import BaseTool, ToolResult


class PriceCalculatorTool(BaseTool):
    """Calculate prices with tax, combos, and discounts"""
    
    name = "calculate_price"
    description = "Calculate order total including tax, apply combo discounts, and validate pricing"
    parameters = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of items with quantities",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "integer"},
                        "unit_price": {"type": "number"}
                    }
                }
            },
            "apply_combo_discount": {
                "type": "boolean",
                "description": "Whether to check and apply combo discounts",
                "default": True
            }
        },
        "required": ["items"]
    }
    
    def __init__(self):
        super().__init__()
        self.tax_rate = 0.0825  # 8.25% tax
        self.combo_discounts = {
            "wing_combo": 2.00,  # $2 off wing combos
            "family_pack": 5.00   # $5 off family packs
        }
    
    async def execute(self, items: List[Dict], apply_combo_discount: bool = True) -> ToolResult:
        """Calculate order total"""
        try:
            subtotal = 0.0
            item_details = []
            
            for item in items:
                qty = item.get("quantity", 1)
                price = item.get("unit_price", 0.0)
                item_total = qty * price
                
                item_details.append({
                    "name": item.get("name", "Unknown"),
                    "quantity": qty,
                    "unit_price": price,
                    "total": item_total
                })
                
                subtotal += item_total
            
            # Calculate combo savings
            combo_savings = 0.0
            if apply_combo_discount:
                combo_savings = self._calculate_combo_savings(items)
            
            # Apply discount
            discounted_subtotal = max(0, subtotal - combo_savings)
            
            # Calculate tax
            tax = discounted_subtotal * self.tax_rate
            
            # Total
            total = discounted_subtotal + tax
            
            return ToolResult(
                success=True,
                data={
                    "subtotal": round(subtotal, 2),
                    "combo_savings": round(combo_savings, 2),
                    "discounted_subtotal": round(discounted_subtotal, 2),
                    "tax": round(tax, 2),
                    "total": round(total, 2),
                    "item_breakdown": item_details,
                    "savings_message": f"You saved ${combo_savings:.2f} with combo pricing!" if combo_savings > 0 else None
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Price calculation failed: {str(e)}")
    
    def _calculate_combo_savings(self, items: List[Dict]) -> float:
        """Calculate potential combo savings"""
        savings = 0.0
        
        # Check for wing + side + drink combo
        has_wings = any("wing" in item.get("name", "").lower() for item in items)
        has_sides = any(item.get("name", "").lower() in ["fries", "veggie sticks"] for item in items)
        has_drinks = any("drink" in item.get("name", "").lower() or item.get("category") == "drinks" for item in items)
        
        if has_wings and (has_sides or has_drinks):
            savings += self.combo_discounts["wing_combo"]
        
        # Check for large orders (family pack)
        total_wings = sum(item.get("quantity", 0) for item in items if "wing" in item.get("name", "").lower())
        if total_wings >= 30:
            savings += self.combo_discounts["family_pack"]
        
        return savings
