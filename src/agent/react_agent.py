"""
ReAct Agent - Fixed conversation flow
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
    """ReAct Agent with proper order flow"""
    
    def __init__(self):
        self.llm = Groq(api_key=settings.groq_api_key)
        self.tools = ToolRegistry().create_default_registry()
        self.working_memory = WorkingMemory(capacity=15)
        self.short_term_memory = ShortTermMemory()
    
    async def process(self, user_message: str, session_id: str) -> str:
        """Process message with full context"""
        
        await self.load_session(session_id)
        self.working_memory.add_turn("user", user_message)
        
        # Extract ALL info from message
        await self._extract_all_info(user_message)
        
        # Generate appropriate response
        response = await self._generate_response(user_message)
        
        self.working_memory.add_turn("assistant", response)
        await self._persist_session(session_id)
        
        return response
    
    async def _extract_all_info(self, message: str):
        """Extract all possible info from message"""
        msg_lower = message.lower().strip()
        customer = self.working_memory.get_customer_info() or {}
        order = self.working_memory.get_current_order() or {"items": []}
        
        # Extract name
        if not customer.get("name"):
            name = self._extract_name(message)
            if name:
                customer["name"] = name
                self.working_memory.set_customer_info(customer)
        
        # Check for completion/done signals
        done_signals = ["that's it", "thats it", "that is it", "done", "complete", 
                       "nothing else", "no thanks", "no thank you", "nithing", "nothing",
                       "that's all", "thats all", "all done", "im good", "i'm good"]
        if any(signal in msg_lower for signal in done_signals):
            order["customer_done"] = True
        
        # Check for "just" items (e.g., "just a ranch", "just fries")
        just_match = re.search(r'just\s+(?:a\s+)?(.+)', msg_lower)
        if just_match:
            item_name = just_match.group(1).strip()
            # Add as a new item
            order["items"].append({
                "name": item_name.capitalize(),
                "quantity": 1,
                "type": "add-on"
            })
        
        # Extract wing quantity
        qty_patterns = [
            r'(\d+)\s*(?:wing|wings|piece|pieces|pc)',
            r'(\d+)\s+(?:wing|wings)',
        ]
        for pattern in qty_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                qty = int(match.group(1))
                # Update or create wing item
                wing_item = self._find_wing_item(order)
                if wing_item:
                    wing_item["quantity"] = qty
                else:
                    order["items"].append({
                        "name": "Wings",
                        "quantity": qty,
                        "type": None,
                        "flavor": None
                    })
                break
        
        # Extract wing type
        if "boneless" in msg_lower:
            wing = self._find_wing_item(order)
            if wing:
                wing["name"] = "Boneless Wings"
                wing["type"] = "boneless"
        elif "classic" in msg_lower or "bone-in" in msg_lower:
            wing = self._find_wing_item(order)
            if wing:
                wing["name"] = "Classic Bone-In Wings"
                wing["type"] = "bone-in"
        
        # Extract flavor
        flavors = ["lemon pepper", "buffalo", "mango habanero", "garlic parmesan", 
                   "atomic", "hickory smoked bbq", "honey mustard", "cajun", 
                   "original hot", "spicy korean", " Louisiana Rub"]
        for flavor in flavors:
            if flavor in msg_lower:
                wing = self._find_wing_item(order)
                if wing:
                    wing["flavor"] = flavor.title()
                break
        
        # Extract dips
        dips = ["ranch", "blue cheese", "honey mustard", "bbq sauce", "buffalo sauce"]
        for dip in dips:
            if dip in msg_lower and "just" not in msg_lower:
                # Check if already added
                existing = [i for i in order["items"] if dip.lower() in i.get("name", "").lower()]
                if not existing:
                    order["items"].append({
                        "name": dip.title() + " Dip",
                        "quantity": 1,
                        "price": 0.99,
                        "type": "dip"
                    })
        
        # Extract sides
        sides = ["fries", "cheese fries", "veggie sticks", "onion rings"]
        for side in sides:
            if side in msg_lower and "just" not in msg_lower:
                existing = [i for i in order["items"] if side.lower() in i.get("name", "").lower()]
                if not existing:
                    prices = {"fries": 3.99, "cheese fries": 4.99, "veggie sticks": 2.99, "onion rings": 4.49}
                    order["items"].append({
                        "name": side.title(),
                        "quantity": 1,
                        "price": prices.get(side, 3.99),
                        "type": "side"
                    })
        
        # Extract order type
        if "pickup" in msg_lower or "pick up" in msg_lower:
            order["order_type"] = "pickup"
        elif "delivery" in msg_lower:
            order["order_type"] = "delivery"
        
        self.working_memory.set_current_order(order)
    
    def _extract_name(self, message: str) -> Optional[str]:
        """Extract name from message"""
        msg_lower = message.lower().strip()
        
        # Skip if it's just an order
        if any(x in msg_lower for x in ["wing", "fries", "dip", "order", "want", "get"]):
            return None
        
        # Common patterns
        patterns = [
            r"(?:name is|i am|i'm|call me|it's|this is)\s+([a-zA-Z]{2,})",
            r"(?:for|name)\s*:?\s*([a-zA-Z]{2,})",
            r"^([a-zA-Z]{2,})$",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg_lower)
            if match:
                name = match.group(1).capitalize()
                # Filter out non-names
                non_names = ["the", "for", "pickup", "delivery", "wings", "boneless", 
                            "classic", "lemon", "buffalo", "mango", "garlic", "atomic"]
                if name.lower() not in non_names:
                    return name
        
        # Single word that looks like a name (2+ letters, no numbers)
        if " " not in message and len(message) >= 2 and message.isalpha():
            name = message.capitalize()
            non_names = ["Wings", "Fries", "Dip", "Ranch", "Buffalo", "Lemon", "Mango"]
            if name not in non_names:
                return name
        
        return None
    
    def _find_wing_item(self, order: Dict) -> Optional[Dict]:
        """Find wing item in order"""
        for item in order.get("items", []):
            if "wing" in item.get("name", "").lower():
                return item
        return None
    
    async def _generate_response(self, user_message: str) -> str:
        """Generate response based on state"""
        
        customer = self.working_memory.get_customer_info() or {}
        order = self.working_memory.get_current_order() or {"items": []}
        name = customer.get("name")
        msg_lower = user_message.lower().strip()
        
        # STATE 1: No name yet
        if not name:
            return "Hey there! I'm Tasha. What's your name?"
        
        # STATE 2: Just got name - greet
        history = self.working_memory.get_recent()
        if len(history) <= 2:
            return f"Hey {name}! Welcome to Wingstop. What can I get for you today?"
        
        # Find wing item
        wing = self._find_wing_item(order)
        
        # Check if customer is done
        if order.get("customer_done"):
            # Need order type?
            if not order.get("order_type"):
                return f"Pickup or delivery, {name}?"
            
            # Have everything - confirm order
            return self._confirm_order(name, order)
        
        # Check for dips/sides request
        if any(x in msg_lower for x in ["just", "add", "get"]):
            # They just added something, ask if that's all
            items = self._format_order_items(order)
            if items:
                return f"Got it. So that's {items}. Anything else?"
        
        # Taking wing order
        if wing:
            # Need quantity
            if not wing.get("quantity"):
                return f"How many wings, {name}?"
            
            # Need type
            if not wing.get("type"):
                return "Boneless or classic bone-in?"
            
            # Need flavor
            if not wing.get("flavor"):
                return "What flavor? Lemon Pepper, Buffalo, Mango Habanero?"
            
            # Wing complete - ask about add-ons
            qty = wing.get("quantity", 0)
            wing_desc = f"{qty} {wing.get('flavor', '')} {wing.get('name', 'wings')}".strip()
            
            return f"Great! {wing_desc}. Anything else - fries, drinks, or dips?"
        
        # No wings yet - ask what they want
        return f"What would you like to order, {name}? We have wings, sides, and drinks."
    
    def _format_order_items(self, order: Dict) -> str:
        """Format order items for display"""
        items = order.get("items", [])
        if not items:
            return "nothing yet"
        
        descriptions = []
        for item in items:
            qty = item.get("quantity", 1)
            name = item.get("name", "")
            flavor = item.get("flavor", "")
            
            if "wing" in name.lower():
                desc = f"{qty} {flavor} {name}" if flavor else f"{qty} {name}"
            else:
                desc = f"{qty} {name}"
            
            descriptions.append(desc.strip())
        
        return ", ".join(descriptions) if descriptions else "nothing yet"
    
    def _confirm_order(self, name: str, order: Dict) -> str:
        """Generate order confirmation"""
        items_desc = self._format_order_items(order)
        order_type = order.get("order_type", "pickup")
        
        # Calculate total
        total = 0
        for item in order.get("items", []):
            qty = item.get("quantity", 1)
            price = item.get("price", 11.99)
            if "wing" in item.get("name", "").lower() and not item.get("price"):
                price = 11.99  # default wing price
            total += qty * price
        
        tax = total * 0.0825
        total_with_tax = total + tax
        
        return f"Perfect {name}! Your order is {items_desc} for {order_type}. Total is ${total_with_tax:.2f}. Ready in 15-20 minutes!"
    
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
