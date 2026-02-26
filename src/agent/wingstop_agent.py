"""
Wingstop Agent - Complete Menu-Aware Ordering System
Acts like a real Wingstop cashier
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.config import settings


class WingType(Enum):
    BONELESS = "boneless"
    BONE_IN = "bone-in"


class WingSize(Enum):
    PC6 = ("6pc", 6)
    PC8 = ("8pc", 8)
    PC10 = ("10pc", 10)
    PC15 = ("15pc", 15)
    PC20 = ("20pc", 20)
    PC30 = ("30pc", 30)


# Wingstop Menu Data
WING_PRICES = {
    ("boneless", 6): 10.99,
    ("boneless", 8): 13.99,
    ("boneless", 10): 16.99,
    ("boneless", 15): 23.99,
    ("boneless", 20): 29.99,
    ("boneless", 30): 42.99,
    ("bone-in", 6): 9.99,
    ("bone-in", 8): 12.99,
    ("bone-in", 10): 15.99,
    ("bone-in", 15): 21.99,
    ("bone-in", 20): 27.99,
    ("bone-in", 30): 39.99,
}

FLAVORS = [
    "Lemon Pepper",
    "Garlic Parmesan",
    "Original Hot",
    "Hickory Smoked BBQ",
    "Mango Habanero",
    "Atomic",
    "Spicy Korean Q",
    "Louisiana Rub",
    "Cajun",
    "Plain"
]

DRY_RUBS = ["Lemon Pepper", "Garlic Parmesan", "Louisiana Rub", "Cajun"]
SAUCES = ["Original Hot", "Hickory Smoked BBQ", "Mango Habanero", "Atomic", "Spicy Korean Q"]

SIDES = {
    "Seasoned Fries": {"regular": 3.49, "large": 4.99},
    "Cheese Fries": 4.49,
    "Veggie Sticks": 3.99,
}

DIPS = {
    "Ranch": 0.99,
    "Blue Cheese": 0.99,
    "Honey Mustard": 0.99,
    "Cheese Sauce": 0.99,
}

DRINKS = {
    "Fountain Drink": {"20oz": 2.49, "32oz": 2.99},
    "Bottled Water": 1.99,
}

COMBOS = {
    "6pc Combo": {"price": 13.99, "savings": 3, "includes": "6 wings + fries + drink"},
    "8pc Combo": {"price": 16.99, "savings": 3, "includes": "8 wings + fries + drink"},
    "10pc Combo": {"price": 19.99, "savings": 3, "includes": "10 wings + fries + drink"},
}


@dataclass
class OrderItem:
    name: str
    wing_type: Optional[str] = None  # boneless, bone-in
    size: Optional[int] = None  # 6, 8, 10, 15, 20, 30
    flavor: Optional[str] = None
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    special_instructions: str = ""
    
    def calculate_price(self):
        if self.wing_type and self.size:
            self.unit_price = WING_PRICES.get((self.wing_type, self.size), 1.29)
            self.total_price = self.quantity * self.unit_price


@dataclass
class Order:
    items: List[OrderItem] = field(default_factory=list)
    sides: List[Dict] = field(default_factory=list)
    dips: List[str] = field(default_factory=list)
    drinks: List[Dict] = field(default_factory=list)
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    order_type: str = "pickup"  # pickup, delivery
    
    @property
    def subtotal(self) -> float:
        total = sum(item.total_price for item in self.items)
        total += sum(s.get("price", 0) for s in self.sides)
        total += sum(DIPS.get(d, 0.99) for d in self.dips)
        total += sum(d.get("price", 2.49) for d in self.drinks)
        return total
    
    @property
    def tax(self) -> float:
        return self.subtotal * 0.08
    
    @property
    def total(self) -> float:
        return self.subtotal + self.tax
    
    def get_last_wing_item(self) -> Optional[OrderItem]:
        """Get the last wing item that might need more details"""
        for item in reversed(self.items):
            if 'wing' in item.name.lower():
                return item
        return None
    
    def is_complete(self) -> bool:
        """Check if order has all required info"""
        if not self.items:
            return False
        
        for item in self.items:
            if 'wing' in item.name.lower():
                if not item.flavor:
                    return False
                if not item.wing_type:
                    return False
                if not item.size:
                    return False
        
        return True
    
    def get_missing_info(self) -> List[str]:
        """Get list of what's missing"""
        missing = []
        
        if not self.items:
            missing.append("items")
            return missing
        
        # Check wing items
        for i, item in enumerate(self.items):
            if 'wing' in item.name.lower():
                if not item.wing_type:
                    missing.append(f"wing_type_{i}")
                if not item.size:
                    missing.append(f"wing_size_{i}")
                if not item.flavor:
                    missing.append(f"wing_flavor_{i}")
        
        if not self.customer_name:
            missing.append("customer_name")
        
        return missing


class WingstopAgent:
    """
    Complete Wingstop ordering agent
    Knows full menu and asks for all required details
    """
    
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
            self.conversations[session_id] = []
        return self.orders[session_id]
    
    def _add_to_conversation(self, session_id: str, role: str, content: str):
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        self.conversations[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def _get_conversation_context(self, session_id: str, n: int = 6) -> str:
        conv = self.conversations.get(session_id, [])
        recent = conv[-n:] if len(conv) > n else conv
        lines = []
        for msg in recent:
            role = "Customer" if msg["role"] == "user" else "Tasha"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
    
    async def process(self, message: str, session_id: str) -> str:
        """Process customer message"""
        order = self._get_order(session_id)
        self._add_to_conversation(session_id, "user", message)
        
        # Extract information from message
        extracted = self._extract_info(message, order)
        
        # Apply extracted info to order
        self._apply_to_order(extracted, order)
        
        # Determine what to ask next
        response = await self._generate_response(message, order, extracted, session_id)
        
        self._add_to_conversation(session_id, "assistant", response)
        return response
    
    def _extract_info(self, message: str, order: Order) -> Dict:
        """Extract all possible info from message"""
        msg_lower = message.lower()
        extracted = {
            "wing_type": None,
            "size": None,
            "flavor": None,
            "quantity": None,
            "name": None,
            "done": False,
            "confirm": False,
            "sides": [],
            "drinks": [],
            "dips": [],
            "_raw": message
        }
        
        # Extract wing type
        if "boneless" in msg_lower:
            extracted["wing_type"] = "boneless"
        elif "bone-in" in msg_lower or "bone in" in msg_lower or "classic" in msg_lower:
            extracted["wing_type"] = "bone-in"
        
        # Extract size
        size_match = re.search(r'(\d+)\s*(?:pc|piece)', msg_lower)
        if size_match:
            extracted["size"] = int(size_match.group(1))
        
        # Extract quantity
        qty_match = re.search(r'(\d+)\s+wing', msg_lower)
        if qty_match and not extracted["size"]:
            extracted["size"] = int(qty_match.group(1))
        
        # Extract flavor
        for flavor in FLAVORS:
            if flavor.lower() in msg_lower:
                extracted["flavor"] = flavor
                break
        
        # Extract name
        name_patterns = [
            r'name is (\w+)',
            r'for (\w+)$',
            r'^(\w+) here',
            r'^it\'?s (\w+)',
            r'under (\w+)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                extracted["name"] = match.group(1).title()
                break
        
        # Check for sides
        for side in SIDES.keys():
            if side.lower() in msg_lower:
                extracted["sides"].append(side)
        
        # Check for dips
        for dip in DIPS.keys():
            if dip.lower() in msg_lower:
                extracted["dips"].append(dip)
        
        # Check for drinks
        for drink in DRINKS.keys():
            if drink.lower() in msg_lower:
                extracted["drinks"].append(drink)
        
        # Check for done
        done_phrases = ['nothing', 'that\'s all', 'no more', 'done', 'finished', 'that\'s it', 'no thanks']
        if any(p in msg_lower for p in done_phrases):
            extracted["done"] = True
        
        # Check for confirm
        if any(w in msg_lower for w in ['confirm', 'place order', 'yes', 'sounds good']):
            extracted["confirm"] = True
        
        return extracted
    
    def _apply_to_order(self, extracted: Dict, order: Order):
        """Apply extracted info to order"""
        msg_lower = extracted.get("_raw", "").lower()
        
        # Check if this is a new wing order
        has_size = extracted["size"] is not None
        has_wing_word = "wing" in msg_lower
        mentions_specific_item = has_size or (has_wing_word and len(msg_lower.split()) <= 5)
        
        # Only create new item if:
        # 1. We have a size (like "10 wings")
        # 2. OR it's a short wing mention without context
        is_new_order = mentions_specific_item and not extracted["flavor"]
        
        # But don't create if we just said "boneless" or similar modifier alone
        is_just_modifier = (
            extracted["wing_type"] and 
            not has_size and 
            not has_wing_word and
            len(msg_lower.split()) <= 2
        )
        
        if is_new_order and not is_just_modifier:
            # New wing order - don't set defaults, wait for user
            wing_type = extracted["wing_type"]  # Could be None
            size = extracted["size"] or 10  # Size we can default
            item = OrderItem(
                name="Wings",  # Generic name until we know type
                wing_type=wing_type,
                size=size,
                quantity=1
            )
            item.calculate_price()
            order.items.append(item)
        
        # Apply flavor/type/size to last wing item
        last_wing = order.get_last_wing_item()
        if last_wing:
            if extracted["flavor"]:
                last_wing.flavor = extracted["flavor"]
            if extracted["wing_type"]:
                last_wing.wing_type = extracted["wing_type"]
                last_wing.name = f"{extracted['wing_type'].title()} Wings"
            if extracted["size"]:
                last_wing.size = extracted["size"]
            # Recalculate price
            last_wing.calculate_price()
        
        # Add sides
        for side in extracted["sides"]:
            if isinstance(SIDES[side], dict):
                order.sides.append({"name": side, "size": "regular", "price": SIDES[side]["regular"]})
            else:
                order.sides.append({"name": side, "price": SIDES[side]})
        
        # Add dips
        order.dips.extend(extracted["dips"])
        
        # Add drinks
        for drink in extracted["drinks"]:
            if isinstance(DRINKS[drink], dict):
                order.drinks.append({"name": drink, "size": "20oz", "price": DRINKS[drink]["20oz"]})
            else:
                order.drinks.append({"name": drink, "price": DRINKS[drink]})
        
        # Set name
        if extracted["name"]:
            order.customer_name = extracted["name"]
    
    async def _generate_response(self, message: str, order: Order, 
                                  extracted: Dict, session_id: str) -> str:
        """Generate appropriate response"""
        
        # Check if confirming
        if extracted["confirm"]:
            if order.is_complete() and order.customer_name:
                return f"Perfect! Order confirmed for {order.customer_name}. Total: ${order.total:.2f}. Ready in 15-20 mins!"
            elif order.items:
                if not order.customer_name:
                    return "What name should I put this order under?"
                missing = order.get_missing_info()
                if missing:
                    return f"Just need a bit more info: {', '.join(missing)}"
        
        # Check if done
        if extracted["done"]:
            if order.items:
                if not order.is_complete():
                    missing = order.get_missing_info()
                    if "customer_name" in missing:
                        return f"Your total is ${order.total:.2f}. What name should I put this under?"
                return f"Thanks! Your total is ${order.total:.2f}. Ready to confirm?"
            return "What can I get started for you?"
        
        # Check last wing item for missing info
        last_wing = order.get_last_wing_item()
        if last_wing:
            if not last_wing.wing_type:
                return f"Would you like those boneless or bone-in?"
            if not last_wing.size:
                return f"What size? We have 6, 8, 10, 15, 20, or 30 piece."
            if not last_wing.flavor:
                return f"What flavor? Popular ones are Lemon Pepper, Garlic Parmesan, and Original Hot."
        
        # Check if we got a name but still need order items
        if order.customer_name and not order.items:
            return f"Thanks {order.customer_name}! What would you like to order?"
        
        # If they just said a type (boneless/bone-in) without a number
        if extracted["wing_type"] and not extracted["size"] and not last_wing:
            return f"Got it, {extracted['wing_type']}. What size? 6, 8, 10, 15, 20, or 30 piece?"
        
        # Default: ask what they want
        if not order.items:
            return "Welcome to Wingstop! Would you like boneless or bone-in wings today?"
        
        # Have items, ask for more
        return "What else can I get you? We also have fries, drinks, and our famous dips."
    
    def get_order_status(self, session_id: str) -> Dict:
        """Get order status"""
        order = self.orders.get(session_id)
        if not order:
            return {"has_order": False}
        
        return {
            "has_order": bool(order.items),
            "items": len(order.items),
            "total": order.total,
            "customer": order.customer_name,
            "complete": order.is_complete(),
            "missing": order.get_missing_info()
        }
