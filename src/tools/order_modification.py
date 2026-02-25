"""
Order Modification Tool
Modify existing orders - add, remove, or change items
"""

from typing import Dict, List, Any, Optional
from src.tools.base import BaseTool, ToolResult
import json
from pathlib import Path


class OrderModificationTool(BaseTool):
    """Modify existing orders"""
    
    name = "modify_order"
    description = "Modify an existing order: add items, remove items, change quantities, or update flavors"
    parameters = {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "Order ID to modify"},
            "action": {
                "type": "string",
                "enum": ["add_item", "remove_item", "change_quantity", "update_flavor"],
                "description": "Modification action"
            },
            "item": {"type": "object", "description": "Item details for the modification"},
            "reason": {"type": "string", "description": "Reason for modification (for logging)"}
        },
        "required": ["order_id", "action"]
    }
    
    def __init__(self, db_path: str = "data/orders.json"):
        super().__init__()
        self.db_path = Path(db_path)
    
    async def execute(
        self,
        order_id: str,
        action: str,
        item: Dict = None,
        reason: str = ""
    ) -> ToolResult:
        """Modify order"""
        try:
            # Load existing orders
            orders = self._load_orders()
            
            # Find order
            order = None
            for o in orders:
                if o.get("id") == order_id:
                    order = o
                    break
            
            if not order:
                return ToolResult(success=False, error=f"Order {order_id} not found")
            
            # Check if order can be modified
            if order.get("status") not in ["pending", "confirmed"]:
                return ToolResult(success=False, error="Order cannot be modified - already in preparation")
            
            # Perform modification
            if action == "add_item":
                result = self._add_item(order, item)
            elif action == "remove_item":
                result = self._remove_item(order, item)
            elif action == "change_quantity":
                result = self._change_quantity(order, item)
            elif action == "update_flavor":
                result = self._update_flavor(order, item)
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")
            
            if not result["success"]:
                return ToolResult(success=False, error=result["error"])
            
            # Log modification
            if "modifications" not in order:
                order["modifications"] = []
            
            from datetime import datetime
            order["modifications"].append({
                "action": action,
                "item": item,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            })
            
            order["updated_at"] = datetime.now().isoformat()
            
            # Save orders
            self._save_orders(orders)
            
            return ToolResult(
                success=True,
                data={
                    "order_id": order_id,
                    "action": action,
                    "current_items": order.get("items", []),
                    "modification_count": len(order["modifications"]),
                    "message": result.get("message", "Order modified successfully")
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Modification failed: {str(e)}")
    
    def _add_item(self, order: Dict, item: Dict) -> Dict:
        """Add item to order"""
        if not item:
            return {"success": False, "error": "No item provided"}
        
        if "items" not in order:
            order["items"] = []
        
        order["items"].append(item)
        return {"success": True, "message": f"Added {item.get('name')} to order"}
    
    def _remove_item(self, order: Dict, item: Dict) -> Dict:
        """Remove item from order"""
        item_name = item.get("name") if item else None
        
        if not item_name or "items" not in order:
            return {"success": False, "error": "Cannot remove item"}
        
        original_count = len(order["items"])
        order["items"] = [i for i in order["items"] if i.get("name") != item_name]
        
        if len(order["items"]) < original_count:
            return {"success": True, "message": f"Removed {item_name} from order"}
        else:
            return {"success": False, "error": f"Item {item_name} not found in order"}
    
    def _change_quantity(self, order: Dict, item: Dict) -> Dict:
        """Change item quantity"""
        item_name = item.get("name") if item else None
        new_qty = item.get("quantity") if item else None
        
        if not item_name or new_qty is None or "items" not in order:
            return {"success": False, "error": "Invalid quantity change"}
        
        for i in order["items"]:
            if i.get("name") == item_name:
                old_qty = i.get("quantity", 0)
                i["quantity"] = new_qty
                return {
                    "success": True,
                    "message": f"Changed {item_name} quantity from {old_qty} to {new_qty}"
                }
        
        return {"success": False, "error": f"Item {item_name} not found"}
    
    def _update_flavor(self, order: Dict, item: Dict) -> Dict:
        """Update item flavor"""
        item_name = item.get("name") if item else None
        new_flavor = item.get("flavor") if item else None
        
        if not item_name or not new_flavor or "items" not in order:
            return {"success": False, "error": "Invalid flavor update"}
        
        for i in order["items"]:
            if i.get("name") == item_name:
                old_flavor = i.get("flavor", "original")
                i["flavor"] = new_flavor
                return {
                    "success": True,
                    "message": f"Changed {item_name} flavor from {old_flavor} to {new_flavor}"
                }
        
        return {"success": False, "error": f"Item {item_name} not found"}
    
    def _load_orders(self) -> List[Dict]:
        """Load orders from file"""
        if not self.db_path.exists():
            return []
        
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def _save_orders(self, orders: List[Dict]):
        """Save orders to file"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(orders, f, indent=2)
