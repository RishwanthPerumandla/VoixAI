"""
Wingstop Cashier Agent - True LLM-Powered
Thinks and talks like a real human cashier
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.config import settings


@dataclass
class OrderItem:
    name: str
    quantity: int = 1
    wing_type: Optional[str] = None  # boneless, bone-in, tenders
    size: Optional[int] = None  # 6, 8, 10, 15, 20, 30
    flavor: Optional[str] = None
    is_combo: bool = False
    sides: List[str] = field(default_factory=list)
    dips: List[str] = field(default_factory=list)
    drinks: List[str] = field(default_factory=list)
    special_instructions: str = ""
    unit_price: float = 0.0
    total_price: float = 0.0


@dataclass
class Order:
    customer_name: Optional[str] = None
    items: List[OrderItem] = field(default_factory=list)
    phone: Optional[str] = None
    order_type: str = "pickup"
    estimated_time: str = "15-20 minutes"
    
    @property
    def total(self) -> float:
        return sum(item.total_price for item in self.items)


class WingstopCashier:
    """
    True LLM-powered cashier that acts human
    Uses Groq for all reasoning and conversation
    """
    
    # Complete Wingstop Menu
    MENU = {
        "wings": {
            "boneless": {"6pc": 10.99, "8pc": 13.99, "10pc": 16.99, "15pc": 23.99, "20pc": 29.99, "30pc": 42.99},
            "bone-in": {"6pc": 9.99, "8pc": 12.99, "10pc": 15.99, "15pc": 21.99, "20pc": 27.99, "30pc": 39.99}
        },
        "tenders": {"4pc": 8.99, "7pc": 13.99},
        "flavors": ["Lemon Pepper", "Garlic Parmesan", "Original Hot", "Hickory Smoked BBQ", 
                   "Mango Habanero", "Atomic", "Spicy Korean Q", "Louisiana Rub", "Cajun"],
        "sides": {"Seasoned Fries": {"regular": 3.49, "large": 4.99}, 
                  "Cheese Fries": 4.49, "Veggie Sticks": 3.99},
        "dips": {"Ranch": 0.99, "Blue Cheese": 0.99, "Honey Mustard": 0.99, "Cheese Sauce": 0.99},
        "drinks": {"Fountain Drink": {"20oz": 2.49, "32oz": 2.99}, "Bottled Water": 1.99},
        "combos": {
            "6pc Combo": {"price": 13.99, "saves": 3, "includes": "6 wings + fries + drink"},
            "8pc Combo": {"price": 16.99, "saves": 3, "includes": "8 wings + fries + drink"},
            "10pc Combo": {"price": 19.99, "saves": 3, "includes": "10 wings + fries + drink"}
        }
    }
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.conversations: Dict[str, List[Dict]] = {}
        self.llm_client = None
        if settings.groq_api_key:
            from groq import Groq
            self.llm_client = Groq(api_key=settings.groq_api_key)
    
    def _get_order(self, session_id: str) -> Order:
        if session_id not in self.orders:
            self.orders[session_id] = Order()
        return self.orders[session_id]
    
    def _add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        self.conversations[session_id].append({
            "role": role, "content": content, "timestamp": datetime.now().isoformat()
        })
    
    def _get_conversation_text(self, session_id: str) -> str:
        conv = self.conversations.get(session_id, [])
        lines = []
        for msg in conv:
            role = "Customer" if msg["role"] == "user" else "Tasha"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
    
    async def process(self, message: str, session_id: str) -> str:
        """Process message through LLM"""
        order = self._get_order(session_id)
        self._add_message(session_id, "user", message)
        
        # Extract items from message first (before LLM)
        self._parse_and_add_item(message, order)
        
        # Use LLM to generate response
        response = await self._llm_process(message, order, session_id)
        
        self._add_message(session_id, "assistant", response)
        return response
    
    async def _llm_process(self, message: str, order: Order, session_id: str) -> str:
        """Main LLM processing - the brain of the cashier"""
        
        if not self.llm_client:
            return "I'm having trouble connecting. Please try again."
        
        conversation = self._get_conversation_text(session_id)
        
        # Build SHORT prompt
        # Check if we should upsell
        last_item_needs = self._get_needs(order)
        should_upsell = last_item_needs == "complete" and len(order.items) > 0 and not any(x in message.lower() for x in ["done", "that\'s all", "complete", "no", "nothing"])
        
        upsell_instruction = ""
        if should_upsell:
            upsell_instruction = "\n- CURRENT ITEM IS COMPLETE - UPSELL: Suggest combo, drink, or dip!"
        
        prompt = f"""You are Tasha, a Wingstop cashier. Keep responses SHORT (under 8 words).

MENU:
Boneless: 6pc $10.99, 8pc $13.99, 10pc $16.99, 15pc $23.99, 20pc $29.99, 30pc $42.99
Classic: 6pc $9.99, 8pc $12.99, 10pc $15.99, 15pc $21.99, 20pc $27.99, 30pc $39.99
Flavors: Lemon Pepper, Garlic Parmesan, Original Hot, Hickory BBQ, Mango Habanero, Atomic, Cajun
RULES:
- KEEP RESPONSES SHORT (5-8 words max)
- Get name first
- Ask: boneless or classic → size → flavor
- When wings COMPLETE: Confirm + Upsell together! "10 classic, got it. Make it a combo?" or "Perfect! Add a drink?"
- Never just say "got it" - always ask for next step{upsell_instruction}

CURRENT ORDER:
Name: {order.customer_name or "?"}
Items: {self._format_items(order.items)}
Total: ${order.total:.2f}
Last item needs: {last_item_needs}

CHAT:
{conversation}

Customer: {message}

Tasha (SHORT reply, 5-8 words):"""

        try:
            response = self.llm_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Tasha, a Wingstop cashier. Keep responses SHORT and SIMPLE."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=30,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[Cashier] LLM error: {e}")
            return self._fallback_response(message, order)
    
    def _fallback_response(self, message: str, order: Order) -> str:
        """Simple fallback"""
        msg_lower = message.lower()
        
        # Get name
        if not order.customer_name:
            name_match = re.search(r'name is (\w+)|for (\w+)|i\'m (\w+)', msg_lower)
            if name_match:
                order.customer_name = next(g for g in name_match.groups() if g)
                return f"Thanks {order.customer_name}! What can I get you today?"
            return "Hey! Thanks for calling Wingstop. Can I get a name for the order?"
        
        # Parse items
        if "wing" in msg_lower or any(x in msg_lower for x in ["6", "8", "10", "15", "20", "30"]):
            # Extract info and add to order
            self._parse_and_add_item(message, order)
            
            # Check what's missing
            last = order.items[-1] if order.items else None
            if last and "wing" in last.name.lower():
                if not last.wing_type:
                    return "Boneless or classic wings?"
                if not last.size:
                    return "What size? We got 6, 8, 10, 15, 20, or 30 piece."
                if not last.flavor:
                    return "What flavor? Our Lemon Pepper is the most popular."
                
                # Complete wing item
                return "Perfect! Want to make that a combo with fries and drink? Saves you $3!"
        
        # Done
        if any(x in msg_lower for x in ["that\'s all", "done", "nothing", "that\'s it"]):
            if order.items:
                return f"Alright, your total is ${order.total:.2f}. It'll be ready in about 15-20 minutes!"
            return "What can I get you?"
        
        return "What else can I get you?"
    
    def _parse_and_add_item(self, message: str, order: Order):
        """Parse items from message and update order"""
        msg_lower = message.lower()
        
        # Extract size
        size_match = re.search(r'(\d+)\s*(?:pc|piece|wings?)', msg_lower)
        size = int(size_match.group(1)) if size_match else None
        
        # Extract type
        wing_type = None
        if "boneless" in msg_lower:
            wing_type = "boneless"
        elif "classic" in msg_lower or "bone-in" in msg_lower or "bone in" in msg_lower or "regular" in msg_lower:
            wing_type = "bone-in"
        
        # Extract flavor
        flavor = None
        for f in self.MENU["flavors"]:
            if f.lower() in msg_lower:
                flavor = f
                break
        
        # Check for existing incomplete wing item
        last_wing = None
        for item in reversed(order.items):
            if "wing" in item.name.lower():
                last_wing = item
                break
        
        if last_wing:
            # Update existing item
            if wing_type and not last_wing.wing_type:
                last_wing.wing_type = wing_type
            if flavor and not last_wing.flavor:
                last_wing.flavor = flavor
            if size and not last_wing.size:
                last_wing.size = size
            
            # Recalculate price if we have all info
            if last_wing.wing_type and last_wing.size:
                price_key = f"{last_wing.size}pc"
                last_wing.unit_price = self.MENU["wings"][last_wing.wing_type].get(price_key, 1.29)
                last_wing.total_price = last_wing.unit_price
            
            return
        
        # New item - only if we have wing keywords
        if size or "wing" in msg_lower:
            item = OrderItem(
                name="Wings",
                wing_type=wing_type,
                size=size,
                flavor=flavor,
                quantity=1
            )
            
            # Calculate price if we have all info
            if wing_type and size:
                price_key = f"{size}pc"
                item.unit_price = self.MENU["wings"][wing_type].get(price_key, 1.29)
                item.total_price = item.unit_price
            
            order.items.append(item)
    
    def _get_needs(self, order: Order) -> str:
        """Get what info is needed for the last item"""
        for item in reversed(order.items):
            if "wing" in item.name.lower():
                needs = []
                if not item.wing_type:
                    needs.append("type")
                if not item.size:
                    needs.append("size")
                if not item.flavor:
                    needs.append("flavor")
                return ", ".join(needs) if needs else "complete"
        return "new item"
    
    def _format_items(self, items: List[OrderItem]) -> str:
        if not items:
            return "None"
        lines = []
        for item in items:
            desc = f"{item.quantity}x {item.name}"
            if item.wing_type:
                desc = f"{item.quantity}x {item.wing_type.title()} Wings"
            if item.size:
                desc += f" ({item.size}pc)"
            if item.flavor:
                desc += f" - {item.flavor}"
            lines.append(desc)
        return "; ".join(lines)
    
    def get_status(self, session_id: str) -> Dict:
        order = self.orders.get(session_id)
        if not order:
            return {"active": False}
        return {
            "active": True,
            "customer": order.customer_name,
            "items": len(order.items),
            "total": order.total
        }
