"""
ReAct Agent - Enhanced with proper order tracking
Phase 2: Full conversation state management
"""

import json
import re
from typing import Any, Dict, List, Optional
from groq import Groq

from src.config import settings
from src.tools.registry import ToolRegistry
from src.memory.working_memory import WorkingMemory
from src.memory.short_term_memory import ShortTermMemory


class ReActAgent:
    """
    ReAct Agent with full order tracking
    """
    
    def __init__(self):
        self.llm = Groq(api_key=settings.groq_api_key)
        self.tools = ToolRegistry().create_default_registry()
        self.working_memory = WorkingMemory(capacity=10)
        self.short_term_memory = ShortTermMemory()
    
    async def process(self, user_message: str, session_id: str) -> str:
        """Process user message with full context"""
        
        # Load existing session
        await self.load_session(session_id)
        
        # Add user message
        self.working_memory.add_turn("user", user_message)
        
        # Extract order info from message
        await self._extract_order_info(user_message)
        
        # Determine action
        action = self._determine_action(user_message)
        
        # Execute action
        tool_result = None
        if action:
            tool_result = await self._execute_action(action, user_message)
        
        # Generate response
        response = await self._generate_response(
            user_message=user_message,
            action=action,
            tool_result=tool_result
        )
        
        # Add assistant response
        self.working_memory.add_turn("assistant", response)
        
        # Persist session
        await self._persist_session(session_id)
        
        return response
    
    async def _extract_order_info(self, message: str):
        """Extract order details from user message"""
        msg_lower = message.lower()
        
        # Extract customer name
        name_patterns = [
            r"(?:name is|i am|i'm|call me)\s+([a-zA-Z]+)",
            r"(?:for|name)\s*:?\s*([a-zA-Z]+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                name = match.group(1).capitalize()
                self.working_memory.set_customer_info({"name": name})
                break
        
        # Extract wing quantity
        qty_match = re.search(r'(\d+)\s*(?:wing|wings|piece|pieces)', msg_lower)
        if qty_match:
            qty = int(qty_match.group(1))
            order = self.working_memory.get_current_order() or {"items": []}
            
            # Find or create wing item
            wing_item = None
            for item in order["items"]:
                if "wing" in item.get("name", "").lower():
                    wing_item = item
                    break
            
            if wing_item:
                wing_item["quantity"] = qty
            else:
                order["items"].append({
                    "name": "Wings",
                    "quantity": qty,
                    "type": "unknown"
                })
            
            self.working_memory.set_current_order(order)
        
        # Extract wing type (boneless/bone-in)
        if "boneless" in msg_lower:
            self._update_wing_type("Boneless Wings")
        elif "bone-in" in msg_lower or "classic" in msg_lower:
            self._update_wing_type("Classic Bone-In Wings")
        
        # Extract flavor
        flavors = ["lemon pepper", "buffalo", "mango habanero", "garlic parmesan", 
                   "atomic", "hickory smoked bbq", "honey mustard", "cajun"]
        for flavor in flavors:
            if flavor in msg_lower:
                self._update_wing_flavor(flavor.title())
                break
        
        # Extract pickup/delivery
        if "pickup" in msg_lower or "pick up" in msg_lower:
            order = self.working_memory.get_current_order() or {}
            order["order_type"] = "pickup"
            self.working_memory.set_current_order(order)
        elif "delivery" in msg_lower:
            order = self.working_memory.get_current_order() or {}
            order["order_type"] = "delivery"
            self.working_memory.set_current_order(order)
    
    def _update_wing_type(self, wing_type: str):
        """Update wing type in order"""
        order = self.working_memory.get_current_order() or {"items": []}
        
        for item in order["items"]:
            if "wing" in item.get("name", "").lower():
                item["name"] = wing_type
                item["type"] = "boneless" if "boneless" in wing_type.lower() else "bone-in"
                break
        else:
            order["items"].append({
                "name": wing_type,
                "quantity": 0,
                "type": "boneless" if "boneless" in wing_type.lower() else "bone-in"
            })
        
        self.working_memory.set_current_order(order)
    
    def _update_wing_flavor(self, flavor: str):
        """Update wing flavor in order"""
        order = self.working_memory.get_current_order() or {"items": []}
        
        for item in order["items"]:
            if "wing" in item.get("name", "").lower():
                item["flavor"] = flavor
                break
        
        self.working_memory.set_current_order(order)
    
    def _determine_action(self, message: str) -> Optional[str]:
        """Determine what action to take"""
        msg_lower = message.lower()
        order = self.working_memory.get_current_order() or {}
        
        # Check for confirmation
        if any(x in msg_lower for x in ["yes", "yeah", "sure", "ok", "okay"]):
            if order.get("pending_confirmation"):
                return "confirm_item"
        
        # Check for menu search
        if any(x in msg_lower for x in ["what do you have", "menu", "flavors", "sauces"]):
            return "search_menu"
        
        # Check for order completion
        if any(x in msg_lower for x in ["that's all", "that's it", "done", "complete", "place order"]):
            return "complete_order"
        
        # Check if we need more info
        if order.get("items"):
            last_item = order["items"][-1]
            if last_item.get("quantity", 0) > 0 and not last_item.get("type"):
                return "ask_wing_type"
            if last_item.get("type") and not last_item.get("flavor"):
                return "ask_flavor"
        
        return None
    
    async def _execute_action(self, action: str, message: str) -> Optional[Dict]:
        """Execute the determined action"""
        
        if action == "search_menu":
            result = await self.tools.execute("search_menu", {"query": message})
            return {"tool": "search_menu", "result": result}
        
        elif action == "complete_order":
            order = self.working_memory.get_current_order()
            customer = self.working_memory.get_customer_info()
            
            if order and order.get("items"):
                result = await self.tools.execute("validate_order", {"order": order})
                
                if result.success and result.data.get("is_valid"):
                    # Create order
                    create_result = await self.tools.execute("create_order", {
                        "customer_name": customer.get("name", "Guest"),
                        "items": order["items"]
                    })
                    return {"tool": "create_order", "result": create_result}
                else:
                    return {"tool": "validate_order", "result": result}
        
        return None
    
    async def _generate_response(self, user_message: str, action: str, tool_result: Optional[Dict]) -> str:
        """Generate response with full context"""
        
        # Build context
        context = self._build_context()
        
        # Build prompt
        prompt = f"""You are Tasha, a friendly Wingstop cashier.

CURRENT ORDER STATE:
{context}

CONVERSATION HISTORY:
{self.working_memory.get_context_for_prompt()}

Customer just said: "{user_message}"
"""
        
        if tool_result:
            prompt += f"\nTool result: {json.dumps(tool_result)}\n"
        
        prompt += "\nRespond as Tasha (keep it under 15 words, friendly):"
        
        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Tasha, a Wingstop cashier. Be friendly, concise, and remember the customer's order."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[Agent] LLM error: {e}")
            return "Sorry, could you repeat that?"
    
    def _build_context(self) -> str:
        """Build current order context"""
        order = self.working_memory.get_current_order()
        customer = self.working_memory.get_customer_info()
        
        if not order:
            return "No order started yet."
        
        context_parts = []
        
        if customer.get("name"):
            context_parts.append(f"Customer: {customer['name']}")
        
        if order.get("items"):
            items_desc = []
            for item in order["items"]:
                qty = item.get("quantity", 0)
                name = item.get("name", "Wings")
                flavor = item.get("flavor", "")
                
                if qty > 0:
                    desc = f"{qty} {name}"
                    if flavor:
                        desc += f" ({flavor})"
                    items_desc.append(desc)
            
            if items_desc:
                context_parts.append(f"Order: {', '.join(items_desc)}")
        
        if order.get("order_type"):
            context_parts.append(f"Type: {order['order_type']}")
        
        return " | ".join(context_parts) if context_parts else "Order started, details pending."
    
    async def _persist_session(self, session_id: str):
        """Save session to Redis"""
        session_data = {
            "working_memory": {
                "turns": self.working_memory.get_recent(),
                "current_order": self.working_memory.get_current_order()
            },
            "customer_info": self.working_memory.get_customer_info()
        }
        await self.short_term_memory.save_session(session_id, session_data)
    
    async def load_session(self, session_id: str):
        """Load session from Redis"""
        session_data = await self.short_term_memory.get_session(session_id)
        if session_data:
            wm_data = session_data.get("working_memory", {})
            for turn in wm_data.get("turns", []):
                self.working_memory.add_turn(turn["role"], turn["content"])
            self.working_memory.set_current_order(wm_data.get("current_order"))
            self.working_memory.set_customer_info(session_data.get("customer_info", {}))
