"""
Order Validation Tool
Validates order completeness and correctness before finalizing
"""

from typing import Dict, List, Any
from src.tools.base import BaseTool, ToolResult


class OrderValidationTool(BaseTool):
    """Validate order before confirmation"""
    
    name = "validate_order"
    description = "Check if order is complete and valid: has items, quantities, flavors, required fields"
    parameters = {
        "type": "object",
        "properties": {
            "order": {"type": "object", "description": "Order to validate"},
            "check_completeness": {"type": "boolean", "default": True}
        },
        "required": ["order"]
    }
    
    def __init__(self):
        super().__init__()
        self.required_flavors = ["wings", "boneless"]
        self.min_order_value = 5.0
    
    async def execute(
        self,
        order: Dict,
        check_completeness: bool = True
    ) -> ToolResult:
        """Validate order"""
        try:
            errors = []
            warnings = []
            suggestions = []
            
            items = order.get("items", [])
            
            # Check has items
            if not items:
                errors.append("Order is empty - add some items first")
                return ToolResult(
                    success=True,
                    data={
                        "is_valid": False,
                        "errors": errors,
                        "warnings": warnings,
                        "suggestions": suggestions,
                        "can_confirm": False
                    }
                )
            
            # Check each item
            for item in items:
                item_name = item.get("name", "Unknown")
                
                # Check quantity
                qty = item.get("quantity", 0)
                if qty <= 0:
                    errors.append(f"{item_name}: Invalid quantity")
                
                # Check wings have flavors
                item_lower = item_name.lower()
                if any(w in item_lower for w in self.required_flavors):
                    if not item.get("flavor") and not item.get("modifiers", {}).get("flavors"):
                        errors.append(f"{item_name}: Please select a flavor")
                
                # Check price exists
                if not item.get("price") and not item.get("unit_price"):
                    warnings.append(f"{item_name}: Price not set")
            
            # Check customer info
            if check_completeness:
                if not order.get("customer_name"):
                    warnings.append("Customer name not provided")
                
                if not order.get("phone") and not order.get("email"):
                    warnings.append("Contact information not provided")
            
            # Check order value
            total = order.get("total_amount", 0)
            if total < self.min_order_value:
                errors.append(f"Minimum order is ${self.min_order_value}")
            
            # Generate suggestions
            if len(items) == 1:
                suggestions.append("Add a side or drink to make it a combo and save $2!")
            
            # Check if any wings without dips
            has_wings = any("wing" in i.get("name", "").lower() for i in items)
            has_dips = any("dip" in i.get("name", "").lower() for i in items)
            if has_wings and not has_dips:
                suggestions.append("Don't forget dips! Ranch and Blue Cheese are popular choices.")
            
            is_valid = len(errors) == 0
            
            return ToolResult(
                success=True,
                data={
                    "is_valid": is_valid,
                    "errors": errors,
                    "warnings": warnings,
                    "suggestions": suggestions,
                    "can_confirm": is_valid,
                    "message": "Order looks good!" if is_valid else f"Please fix: {', '.join(errors[:2])}"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Validation failed: {str(e)}")
