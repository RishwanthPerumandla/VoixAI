"""
Policy Checker Tool
Validates orders against business rules
"""

from typing import Dict, List, Any
from src.tools.base import BaseTool, ToolResult


class PolicyCheckerTool(BaseTool):
    """Check orders against business policies"""
    
    name = "check_policy"
    description = "Validate order against business rules: hours, limits, availability, refund policy"
    parameters = {
        "type": "object",
        "properties": {
            "order": {"type": "object", "description": "Order to validate"},
            "check_type": {
                "type": "string",
                "enum": ["hours", "order_limits", "refund_eligible", "all"],
                "default": "all"
            }
        },
        "required": ["order"]
    }
    
    def __init__(self):
        super().__init__()
        self.policies = {
            "max_order_value": 200.0,
            "max_items": 50,
            "min_order_value": 5.0,
            "refund_window_hours": 2,
            "hours": {
                "open": 10,  # 10 AM
                "close": 22  # 10 PM
            }
        }
    
    async def execute(
        self,
        order: Dict,
        check_type: str = "all"
    ) -> ToolResult:
        """Check order against policies"""
        try:
            violations = []
            warnings = []
            
            if check_type in ["hours", "all"]:
                hour_check = self._check_hours()
                if not hour_check["valid"]:
                    violations.append(hour_check["message"])
            
            if check_type in ["order_limits", "all"]:
                limit_checks = self._check_order_limits(order)
                violations.extend(limit_checks["violations"])
                warnings.extend(limit_checks["warnings"])
            
            if check_type in ["refund_eligible", "all"]:
                refund_check = self._check_refund_eligibility(order)
                if not refund_check["eligible"]:
                    warnings.append(refund_check["message"])
            
            is_valid = len(violations) == 0
            
            return ToolResult(
                success=True,
                data={
                    "is_valid": is_valid,
                    "violations": violations,
                    "warnings": warnings,
                    "can_proceed": is_valid,
                    "message": "Order valid" if is_valid else f"Issues found: {', '.join(violations)}"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Policy check failed: {str(e)}")
    
    def _check_hours(self) -> Dict:
        """Check if within operating hours"""
        from datetime import datetime
        
        now = datetime.now()
        current_hour = now.hour
        
        if self.policies["hours"]["open"] <= current_hour < self.policies["hours"]["close"]:
            return {"valid": True}
        else:
            return {
                "valid": False,
                "message": f"Restaurant closed. Hours: {self.policies['hours']['open']}AM - {self.policies['hours']['close']}PM"
            }
    
    def _check_order_limits(self, order: Dict) -> Dict:
        """Check order value and item limits"""
        violations = []
        warnings = []
        
        items = order.get("items", [])
        total_value = order.get("total_amount", 0)
        
        # Check max items
        total_qty = sum(item.get("quantity", 0) for item in items)
        if total_qty > self.policies["max_items"]:
            violations.append(f"Maximum {self.policies['max_items']} items per order")
        
        # Check order value
        if total_value > self.policies["max_order_value"]:
            violations.append(f"Maximum order value is ${self.policies['max_order_value']}")
        
        if total_value < self.policies["min_order_value"] and total_value > 0:
            warnings.append(f"Minimum order is ${self.policies['min_order_value']}")
        
        return {"violations": violations, "warnings": warnings}
    
    def _check_refund_eligibility(self, order: Dict) -> Dict:
        """Check if order is eligible for refund"""
        from datetime import datetime, timedelta
        
        order_time_str = order.get("created_at")
        if not order_time_str:
            return {"eligible": False, "message": "Order time unknown"}
        
        try:
            # Parse order time
            order_time = datetime.fromisoformat(order_time_str.replace('Z', '+00:00'))
            current_time = datetime.now(order_time.tzinfo)
            
            hours_since = (current_time - order_time).total_seconds() / 3600
            
            if hours_since > self.policies["refund_window_hours"]:
                return {
                    "eligible": False,
                    "message": f"Refund window ({self.policies['refund_window_hours']} hours) has passed"
                }
            
            return {"eligible": True, "message": "Eligible for refund"}
            
        except:
            return {"eligible": False, "message": "Cannot determine refund eligibility"}
