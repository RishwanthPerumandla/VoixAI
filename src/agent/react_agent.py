"""
ReAct Agent - Proper Wingstop Flow
Name first, then order
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
    ReAct Agent with proper Wingstop conversation flow:
    1. Greeting + Get name
    2. Take order (with name known)
    3. Confirm and complete
    """
    
    def __init__(self):
        self.llm = Groq(api_key=settings.groq_api_key)
        self.tools = ToolRegistry().create_default_registry()
        self.working_memory = WorkingMemory(capacity=10)
        self.short_term_memory = ShortTermMemory()
        self.greeted = False
    
    async def process(self, user_message: str, session_id: str) -> str:
        """Process user message with proper flow"""
        
        # Load existing session
        await self.load_session(session_id)
        
        # Add user message
        self.working_memory.add_turn("user", user_message)
        
        # Extract info from message
        await self._extract_info(user_message)
        
        # Determine response based on state
        response = await self._generate_response(user_message)
        
        # Add assistant response
        self.working_memory.add_turn("assistant", response)
        
        # Persist session
        await self._persist_session(session_id)
        
        return response
    
    async def _extract_info(self, message: str):
        """Extract all info from user message"""
        msg_lower = message.lower()
        customer = self.working_memory.get_customer_info() or {}
        order = self.working_memory.get_current_order() or {"items": []}
        
        # Extract name (only if not already have it)
        if not customer.get("name"):
            name = self._extract_name(message)
            if name:
                customer["name"] = name
                self.working_memory.set_customer_info(customer)
        
        # Extract wing quantity
        qty_match = re.search(r'(\d+)\s*(?:wing|wings|piece|pieces)', msg_lower)
        if qty_match:
            qty = int(qty_match.group(1))
            
            # Find existing wing item or create new
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
                    "type": None,
                    "flavor": None
                })
        
        # Extract wing type
        if "boneless" in msg_lower:
            self._update_wing_field(order, "name", "Boneless Wings")
            self._update_wing_field(order, "type", "boneless")
        elif "bone-in" in msg_lower or "classic" in msg_lower:
            self._update_wing_field(order, "name", "Classic Bone-In Wings")
            self._update_wing_field(order, "type", "bone-in")
        
        # Extract flavor
        flavors = ["lemon pepper", "buffalo", "mango habanero", "garlic parmesan", 
                   "atomic", "hickory smoked bbq", "honey mustard", "cajun", "original hot"]
        for flavor in flavors:
            if flavor in msg_lower:
                self._update_wing_field(order, "flavor", flavor.title())
                break
        
        # Extract pickup/delivery
        if "pickup" in msg_lower or "pick up" in msg_lower:
            order["order_type"] = "pickup"
        elif "delivery" in msg_lower:
            order["order_type"] = "delivery"
        
        # Handle confirmation
        if any(x in msg_lower for x in ["yes", "yeah", "sure", "ok", "okay", "perfect"]):
            if order.get("pending_confirmation"):
                order["confirmed"] = True
                order["pending_confirmation"] = False
        
        self.working_memory.set_current_order(order)
    
    def _extract_name(self, message: str) -> Optional[str]:
        """Extract name from message"""
        msg_lower = message.lower()
        
        # Common name patterns
        patterns = [
            r"(?:name is|i am|i'm|call me|it's|this is)\s+([a-zA-Z]+)",
            r"(?:for|name)\s*:?\s*([a-zA-Z]+)",
            r"^([a-zA-Z]+)$",  # Just a name
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg_lower)
            if match:
                name = match.group(1).capitalize()
                # Filter out common non-names
                if name.lower() not in ["the", "for", "pickup", "delivery", "wings", "boneless"]:
                    return name
        
        return None
    
    def _update_wing_field(self, order: Dict, field: str, value: str):
        """Update a field on the wing item"""
        for item in order["items"]:
            if "wing" in item.get("name", "").lower() or item.get("name") == "Wings":
                item[field] = value
                return
        
        # No wing item yet, create one
        order["items"].append({
            "name": "Wings",
            "quantity": 0,
            "type": None,
            "flavor": None,
            field: value
        })
    
    async def _generate_response(self, user_message: str) -> str:
        """Generate response based on conversation state"""
        
        customer = self.working_memory.get_customer_info() or {}
        order = self.working_memory.get_current_order() or {"items": []}
        name = customer.get("name")
        
        # STATE 1: No name yet - must get name first
        if not name:
            return "Hey there! I'm Tasha. What's your name?"
        
        # STATE 2: Have name, greeting
        history = self.working_memory.get_recent()
        just_got_name = len(history) <= 2 and customer.get("name")
        
        if just_got_name or not order.get("greeted"):
            order["greeted"] = True
            self.working_memory.set_current_order(order)
            return f"Hey {name}! Welcome to Wingstop. What can I get for you today?"
        
        # STATE 3: Taking order - check what we need
        
        # Check if order complete
        if order.get("confirmed") and order.get("order_type"):
            return self._finalize_order(name, order)
        
        # Check for completion intent
        msg_lower = user_message.lower()
        if any(x in msg_lower for x in ["that's all", "that's it", "done", "complete", "place order"]):
            return self._ask_confirmation(name, order)
        
        # Check wing item status
        wing_item = None
        for item in order["items"]:
            if "wing" in item.get("name", "").lower():
                wing_item = item
                break
        
        if wing_item:
            # Need quantity?
            if not wing_item.get("quantity"):
                return f"How many wings would you like, {name}?"
            
            # Need type?
            if not wing_item.get("type"):
                return "Boneless or classic bone-in?"
            
            # Need flavor?
            if not wing_item.get("flavor"):
                return "What flavor? We have Lemon Pepper, Buffalo, Mango Habanero, and more!"
            
            # Have wing details, ask for more or confirmation
            if not order.get("asked_additions"):
                order["asked_additions"] = True
                self.working_memory.set_current_order(order)
                return f"Great! {wing_item['quantity']} {wing_item['flavor']} {wing_item['name']}. Anything else - fries, drinks, or dips?"
            
            # Waiting for more items or done
            if any(x in msg_lower for x in ["no", "nothing", "that's it", "done"]):
                return self._ask_confirmation(name, order)
        
        # No wing item yet, ask what they want
        return f"What would you like to order, {name}? We have wings, sides, and drinks."
    
    def _ask_confirmation(self, name: str, order: Dict) -> str:
        """Ask for order confirmation"""
        # Build order summary
        items_desc = []
        for item in order.get("items", []):
            qty = item.get("quantity", 0)
            item_name = item.get("name", "")
            flavor = item.get("flavor", "")
            
            if qty > 0:
                desc = f"{qty} {flavor} {item_name}" if flavor else f"{qty} {item_name}"
                items_desc.append(desc)
        
        if not items_desc:
            return f"What can I get you, {name}?"
        
        order_summary = ", ".join(items_desc)
        order["pending_confirmation"] = True
        self.working_memory.set_current_order(order)
        
        return f"Okay {name}, that's {order_summary}. Pickup or delivery?"
    
    def _finalize_order(self, name: str, order: Dict) -> str:
        """Complete the order"""
        order_type = order.get("order_type", "pickup")
        
        # Calculate total
        total = 0
        for item in order.get("items", []):
            qty = item.get("quantity", 0)
            price = item.get("price", 11.99)  # default price
            total += qty * price
        
        tax = total * 0.0825
        total_with_tax = total + tax
        
        # Create order in database
        # (This would call the create_order tool in production)
        
        return f"Perfect! Your order is ${total_with_tax:.2f} for {order_type}. It'll be ready in 15-20 minutes, {name}!"
    
    async def _persist_session(self, session_id: str):
        """Save session"""
        session_data = {
            "working_memory": {
                "turns": self.working_memory.get_recent(),
                "current_order": self.working_memory.get_current_order()
            },
            "customer_info": self.working_memory.get_customer_info()
        }
        await self.short_term_memory.save_session(session_id, session_data)
    
    async def load_session(self, session_id: str):
        """Load session"""
        session_data = await self.short_term_memory.get_session(session_id)
        if session_data:
            wm_data = session_data.get("working_memory", {})
            for turn in wm_data.get("turns", []):
                self.working_memory.add_turn(turn["role"], turn["content"])
            self.working_memory.set_current_order(wm_data.get("current_order"))
            self.working_memory.set_customer_info(session_data.get("customer_info", {}))
