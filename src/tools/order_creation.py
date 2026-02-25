"""
Order Creation Tool - Phase 1.6 (Basic)
Creates orders in SQLite for local development
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from src.tools.base import BaseTool, ToolResult


class OrderCreationTool(BaseTool):
    """Create a new order"""
    
    name = "create_order"
    description = "Create a new order with items, calculate total, and save to database."
    parameters = {
        "type": "object",
        "properties": {
            "customer_name": {
                "type": "string",
                "description": "Customer name for the order"
            },
            "items": {
                "type": "array",
                "description": "List of order items",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "integer"},
                        "price": {"type": "number"},
                        "modifiers": {"type": "object"}
                    },
                    "required": ["name", "quantity", "price"]
                }
            },
            "conversation_id": {
                "type": "string",
                "description": "Conversation session ID"
            }
        },
        "required": ["customer_name", "items"]
    }
    
    def __init__(self, db_path: str = "data/voixai.db"):
        super().__init__()
        self.db_path = Path(db_path)
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database directory exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _calculate_total(self, items: List[Dict]) -> float:
        """Calculate order total"""
        total = 0.0
        for item in items:
            qty = item.get("quantity", 1)
            price = item.get("price", 0.0)
            total += qty * price
        
        # Add tax (8.25%)
        tax = total * 0.0825
        return round(total + tax, 2)
    
    async def execute(
        self, 
        customer_name: str, 
        items: List[Dict],
        conversation_id: str = None
    ) -> ToolResult:
        """Create a new order"""
        try:
            # Validate items
            if not items:
                return ToolResult(
                    success=False,
                    error="Order must contain at least one item"
                )
            
            # Calculate total
            total = self._calculate_total(items)
            
            # Create order object
            order = {
                "id": str(uuid.uuid4()),
                "customer_name": customer_name,
                "items": items,
                "subtotal": round(total / 1.0825, 2),
                "tax": round(total - (total / 1.0825), 2),
                "total": total,
                "status": "pending",
                "conversation_id": conversation_id,
                "created_at": datetime.now().isoformat()
            }
            
            # Save to JSON file (SQLite will come in Phase 2)
            orders_file = self.db_path.parent / "orders.json"
            
            # Load existing orders
            orders = []
            if orders_file.exists():
                with open(orders_file, 'r') as f:
                    orders = json.load(f)
            
            # Add new order
            orders.append(order)
            
            # Save back
            with open(orders_file, 'w') as f:
                json.dump(orders, f, indent=2)
            
            return ToolResult(
                success=True,
                data={
                    "order_id": order["id"],
                    "customer_name": customer_name,
                    "items_count": len(items),
                    "total": total,
                    "status": "pending",
                    "message": f"Order created successfully for {customer_name}. Total: ${total:.2f}"
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Order creation failed: {str(e)}"
            )
