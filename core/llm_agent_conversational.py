"""Conversational LLM Agent with State Machine for Wingstop Ordering"""
import os
import json
import re
from enum import Enum, auto
from typing import Tuple, Optional, Dict, List, Any
from dataclasses import dataclass, field
from groq import Groq


class DialogueState(Enum):
    """Conversational state machine states"""
    GREETING = "greeting"
    ASKING_NAME = "asking_name"                # For call-in: customer name
    ASKING_MAIN_ITEM = "asking_main_item"      # How many wings? Bone-in or boneless?
    ASKING_FLAVOR = "asking_flavor"            # What flavors?
    ASKING_COMBO = "asking_combo"              # Make it a combo?
    ASKING_DRINK = "asking_drink"              # What drink? What size?
    ASKING_SIDES = "asking_sides"              # Fries or veggie sticks?
    ASKING_DIP = "asking_dip"                  # What dip?
    CONFIRMING = "confirming"                  # Review order with price
    MODIFYING = "modifying"                    # Fixing something
    COMPLETED = "completed"                    # Order done


@dataclass
class OrderItem:
    """Represents an item in the order"""
    name: str
    qty: int
    category: str = ""
    modifiers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "qty": self.qty,
            "category": self.category,
            "modifiers": self.modifiers
        }


@dataclass
class CurrentOrder:
    """Tracks the current order being built"""
    customer_name: str = ""
    wing_qty: int = 0
    wing_type: str = ""          # boneless, bone-in
    flavors: List[Dict[str, Any]] = field(default_factory=list)
    is_combo: bool = False
    combo_decided: bool = False
    drink: str = ""
    drink_size: str = ""
    side: str = ""
    dip: str = ""
    extras: List[OrderItem] = field(default_factory=list)
    
    def has_wings(self) -> bool:
        return self.wing_qty > 0
    
    def get_flavor_summary(self) -> str:
        if not self.flavors:
            return "no flavor selected"
        parts = []
        for f in self.flavors:
            parts.append(f"{f.get('qty', 0)} {f.get('flavor', '')}")
        return ", ".join(parts)
    
    def to_items_list(self) -> List[Dict]:
        """Convert to list of items for storage"""
        items = []
        if self.has_wings():
            wing_item = {
                "name": f"{self.wing_type} wings" if self.wing_type else "wings",
                "qty": self.wing_qty,
                "category": "wings",
                "modifiers": {
                    "flavors": self.flavors,
                    "type": self.wing_type
                }
            }
            items.append(wing_item)
        
        if self.is_combo or self.drink:
            drink_item = {
                "name": self.drink or "drink",
                "qty": 1,
                "category": "drink",
                "modifiers": {"size": self.drink_size}
            }
            items.append(drink_item)
        
        if self.side:
            side_item = {
                "name": self.side,
                "qty": 1,
                "category": "side",
                "modifiers": {}
            }
            items.append(side_item)
        
        if self.dip:
            dip_item = {
                "name": self.dip,
                "qty": 1,
                "category": "dip",
                "modifiers": {}
            }
            items.append(dip_item)
        
        items.extend([item.to_dict() for item in self.extras])
        return items


class ConversationalAgent:
    """Tasha - Wingstop Cashier with Conversational State Machine"""
    
    # Menu items
    FLAVORS = ["lemon pepper", "cajun", "garlic parmesan", "hickory smoked bbq", 
               "mild", "original hot", "atomic", "mango habanero", "korean bbq", 
               "spicy korean", "louisiana rub", "buffalo"]
    
    DRINKS = ["coke", "diet coke", "sprite", "dr pepper", "diet dr pepper",
              "lemonade", "strawberry lemonade", "mango lemonade", "iced tea",
              "sweet tea", "unsweetened tea", "fruit punch"]
    
    DIPS = ["ranch", "blue cheese", "honey mustard", "cheese sauce", "teriyaki"]
    
    SIDES = ["seasoned fries", "veggie sticks", "cheese fries", "buffalo ranch fries",
             "cajun corn", "coleslaw"]
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Groq client"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=api_key)
        self.config = config
        self.model_name = config.get("model", "llama-3.3-70b-versatile")
        self.temperature = config.get("temperature", 0.2)  # Lower for more consistent
        self.max_tokens = config.get("max_tokens", 80)   # Shorter for speed
        
        # State
        self.state = DialogueState.GREETING
        self.order = CurrentOrder()
        self.conversation_history: List[Dict] = []
        
        # Price estimates
        self.wing_price = 1.29
        self.combo_savings = 3.00
        
    def _get_system_prompt(self) -> str:
        """Get system prompt based on current state"""
        order_summary = self._get_order_summary_text()
        
        base_prompt = "You are Tasha, a friendly Wingstop cashier. "
        base_prompt += f"Current state: {self.state.value}. "
        base_prompt += f"Order so far: {order_summary}.\n\n"
        
        # State-specific instructions - VERY explicit about what we have and what to ask
        if self.state == DialogueState.GREETING:
            if self.order.wing_qty > 0 and not self.order.customer_name:
                base_prompt += f"We have {self.order.wing_qty} wings. We NEED the customer's name. Ask: 'Gotcha, {self.order.wing_qty} wings! Can I get your name?'"
            else:
                base_prompt += "GREET and ask for name: 'Hey! Welcome to Wingstop! I'm Tasha. Can I get your name for the order?'"
        
        elif self.state == DialogueState.ASKING_NAME:
            base_prompt += f"We have {self.order.wing_qty} wings. We NEED the customer's name. Ask: 'Gotcha! And your name?'"
        
        elif self.state == DialogueState.ASKING_MAIN_ITEM:
            base_prompt += f"Customer {self.order.customer_name} wants {self.order.wing_qty} wings. We NEED to know bone-in or boneless. Ask: 'Bone-in or boneless?'"
        
        elif self.state == DialogueState.ASKING_FLAVOR:
            base_prompt += f"We have {self.order.wing_qty} {self.order.wing_type} wings for {self.order.customer_name}. Ask 'What flavors? You can pick up to 2.'"
        
        elif self.state == DialogueState.ASKING_COMBO:
            base_prompt += f"They have {self.order.wing_qty} wings. Ask 'Want to make that a combo with fries and a drink?'"
        
        elif self.state == DialogueState.ASKING_DRINK:
            base_prompt += "Ask 'What to drink? We got Coke, Diet, Sprite, lemonade.'"
        
        elif self.state == DialogueState.ASKING_SIDES:
            base_prompt += "Ask 'Seasoned fries or veggie sticks?'"
        
        elif self.state == DialogueState.ASKING_DIP:
            base_prompt += "Ask 'What dip? Ranch, blue cheese, or honey mustard?'"
        
        elif self.state == DialogueState.CONFIRMING:
            price = self._calculate_price()
            base_prompt += f"CONFIRM: 'So that's {order_summary}. Total is ${price:.2f}. Look right?'"
        
        elif self.state == DialogueState.COMPLETED:
            price = self._calculate_price()
            base_prompt += f"DONE: 'Perfect! Ready in 15-20 mins, {self.order.customer_name}. Total ${price:.2f}. See you then!'"
        
        # Universal rules
        base_prompt += "\n\nRULES:\n"
        base_prompt += "- Keep responses SHORT (under 12 words)\n"
        base_prompt += "- Use casual speech: 'lemme', 'gonna', 'gotcha'\n"
        base_prompt += "- Always confirm what you heard\n"
        base_prompt += "- If they say a full order at once, confirm it all\n"
        base_prompt += "- NEVER say 'As an AI' or formal phrases\n"
        
        return base_prompt
    
    def _get_order_summary_text(self) -> str:
        """Get human-readable order summary"""
        parts = []
        if self.order.has_wings():
            wing_desc = f"{self.order.wing_qty} {self.order.wing_type or ''} wings"
            if self.order.flavors:
                wing_desc += f" ({self.order.get_flavor_summary()})"
            parts.append(wing_desc)
        
        if self.order.is_combo:
            parts.append("combo")
        
        if self.order.drink:
            drink_desc = self.order.drink
            if self.order.drink_size:
                drink_desc += f" {self.order.drink_size}"
            parts.append(drink_desc)
        
        if self.order.side:
            parts.append(self.order.side)
        
        if self.order.dip:
            parts.append(f"{self.order.dip} dip")
        
        return ", ".join(parts) if parts else "(nothing yet)"
    
    def process(self, user_text: str) -> Tuple[str, Optional[Dict]]:
        """Process user input and return response"""
        user_lower = user_text.lower().strip()
        print(f"\n[Agent] Input: '{user_text[:50]}...' | State: {self.state.value}")
        
        # If already completed
        if self.state == DialogueState.COMPLETED:
            return f"Your order's already in, {self.order.customer_name}! See you soon!", self._get_order_data()
        
        # Handle repeat order
        if any(phrase in user_lower for phrase in ["repeat", "what did i order"]):
            return self._handle_repeat_order(), self._get_order_data()
        
        # Extract all info from text
        self._extract_all_info(user_text)
        
        # Handle special intents
        if any(phrase in user_lower for phrase in ["total", "price", "how much", "pricing"]):
            if self.order.has_wings():
                self.state = DialogueState.CONFIRMING
                return self._generate_confirmation(), self._get_order_data()
        
        # Handle suggestion requests
        if any(word in user_lower for word in ["suggest", "recommend", "what's good", "what do you like", "best flavor"]):
            return self._get_suggestion_response(), self._get_order_data()
        
        # Handle "yes" to accept suggested flavor when in ASKING_FLAVOR
        if self.state == DialogueState.ASKING_FLAVOR:
            if any(phrase in user_lower for phrase in ["yes", "go with it", "sounds good", "perfect", "that's good", "do it"]):
                # User accepted the suggested Lemon Pepper
                if not self.order.flavors:
                    self.order.flavors.append({'flavor': 'lemon pepper', 'qty': self.order.wing_qty})
                    print(f"[Agent] User accepted suggestion: lemon pepper x{self.order.wing_qty}")
        
        # State transitions
        self._update_state(user_lower)
        print(f"[Agent] New state: {self.state.value}")
        
        # Get response - use hardcoded for simple states, LLM for complex
        response = self._get_state_response()
        if not response:
            response = self._get_llm_response(user_text)
            response = self._clean_response(response)
        
        return response, self._get_order_data()
    
    def _extract_all_info(self, text: str):
        """Extract all possible info from text"""
        text_lower = text.lower()
        
        # Extract name (for call-in)
        if self.state == DialogueState.GREETING or self.state == DialogueState.ASKING_NAME:
            # Look for name patterns
            name_patterns = [
                r'name is (\w+)',
                r'it\'s (\w+)',
                r'this is (\w+)',
                r'(\w+) here',
                r'for (\w+)',
                r'order (?:for|in the name of) (\w+)',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    self.order.customer_name = match.group(1).capitalize()
                    print(f"[Agent] Extracted name: {self.order.customer_name}")
                    break
        
        # Extract wing quantity
        qty_match = re.search(r'(\d+)\s*(?:piece|pc|wing|wings)?', text_lower)
        if qty_match:
            qty = int(qty_match.group(1))
            if 1 <= qty <= 100:
                self.order.wing_qty = qty
                print(f"[Agent] Extracted wing qty: {qty}")
        
        # Extract wing type
        if 'boneless' in text_lower:
            self.order.wing_type = 'boneless'
        elif 'bone-in' in text_lower or 'bone in' in text_lower:
            self.order.wing_type = 'bone-in'
        
        # Extract flavors with fuzzy matching
        self._extract_flavors_fuzzy(text_lower)
        
        # Extract combo preference
        if 'no combo' in text_lower or 'dont want a combo' in text_lower or "don't want a combo" in text_lower:
            self.order.is_combo = False
            self.order.combo_decided = True
            print("[Agent] Combo declined")
        elif 'make it a combo' in text_lower or 'yes combo' in text_lower:
            self.order.is_combo = True
            self.order.combo_decided = True
            print("[Agent] Combo accepted")
        
        # Extract drink
        for drink in self.DRINKS:
            if drink in text_lower:
                self.order.drink = drink
                if '32' in text_lower or 'large' in text_lower:
                    self.order.drink_size = '32oz'
                else:
                    self.order.drink_size = '20oz'
                print(f"[Agent] Extracted drink: {drink}")
                break
        
        # Extract side
        for side in self.SIDES:
            if side in text_lower:
                self.order.side = side
                print(f"[Agent] Extracted side: {side}")
                break
        
        # Extract dip
        for dip in self.DIPS:
            if dip in text_lower:
                self.order.dip = dip
                print(f"[Agent] Extracted dip: {dip}")
                break
    
    def _normalize_flavors(self):
        """Ensure flavor quantities add up to wing quantity"""
        if not self.order.flavors or self.order.wing_qty == 0:
            return
        
        total = sum(f.get('qty', 0) for f in self.order.flavors)
        if total != self.order.wing_qty:
            # Adjust last flavor
            diff = self.order.wing_qty - total
            if self.order.flavors:
                self.order.flavors[-1]['qty'] = max(1, self.order.flavors[-1]['qty'] + diff)
    
    def _extract_flavors_fuzzy(self, text_lower: str):
        """Extract flavors with fuzzy matching for common misheard words"""
        # Common STT mistakes and their corrections
        fuzzy_mappings = {
            'lemon clipper': 'lemon pepper',
            'lemon paper': 'lemon pepper',
            'lemon peper': 'lemon pepper',
            'lemonpepper': 'lemon pepper',
            'cajan': 'cajun',
            'cajun spice': 'cajun',
            'garlic parm': 'garlic parmesan',
            'garlic parmesian': 'garlic parmesan',
            'bbq': 'hickory smoked bbq',
            'barbecue': 'hickory smoked bbq',
            'buffalo hot': 'atomic',
            'atomic hot': 'atomic',
            'original': 'original hot',
            'hot wings': 'original hot',
            'korean': 'korean bbq',
            'louisana': 'louisiana rub',
            'louisianna': 'louisiana rub',
        }
        
        # First try exact match
        for flavor in self.FLAVORS:
            if flavor in text_lower:
                self._add_flavor(flavor, text_lower)
                return
        
        # Then try fuzzy match
        for misheard, correct in fuzzy_mappings.items():
            if misheard in text_lower:
                print(f"[Agent] Fuzzy match: '{misheard}' -> '{correct}'")
                self._add_flavor(correct, text_lower)
                return
    
    def _add_flavor(self, flavor: str, text_lower: str):
        """Add a flavor to the order"""
        # Check for qty before flavor
        qty_match = re.search(rf'(\d+)\s+(?:of\s+)?{re.escape(flavor)}', text_lower)
        if qty_match:
            flavor_qty = int(qty_match.group(1))
        else:
            # Default split
            flavor_qty = self.order.wing_qty // max(1, len(self.order.flavors) + 1)
        
        existing = next((f for f in self.order.flavors if f['flavor'] == flavor), None)
        if existing:
            existing['qty'] = flavor_qty
        else:
            self.order.flavors.append({'flavor': flavor, 'qty': flavor_qty})
        
        print(f"[Agent] Extracted flavor: {flavor} x{flavor_qty}")
        self._normalize_flavors()
    
    def _update_state(self, user_lower: str):
        """Update state based on current state and extracted info"""
        
        # Handle yes/no in current state context
        if any(w in user_lower for w in ['yes', 'yeah', 'yep', 'sure', 'ok']):
            if self.state == DialogueState.ASKING_COMBO:
                self.order.is_combo = True
                self.order.combo_decided = True
                self.state = DialogueState.ASKING_DRINK if not self.order.drink else DialogueState.ASKING_SIDES
                return
            elif self.state == DialogueState.CONFIRMING:
                self.state = DialogueState.COMPLETED
                return
        
        if any(w in user_lower for w in ['no', 'nope', 'nah']):
            if self.state == DialogueState.ASKING_COMBO:
                self.order.is_combo = False
                self.order.combo_decided = True
                self.state = DialogueState.CONFIRMING if self.order.flavors else DialogueState.ASKING_FLAVOR
                return
            elif self.state == DialogueState.CONFIRMING:
                self.state = DialogueState.MODIFYING
                return
        
        # Handle "that's all"
        if any(p in user_lower for p in ["that's all", "that's it", "done", "nothing else", "dont need", "don't need"]):
            if self.order.wing_qty >= 6 and not self.order.combo_decided:
                self.order.combo_decided = True
                self.order.is_combo = False
            self.state = DialogueState.CONFIRMING
            return
        
        # State progression
        if self.state == DialogueState.GREETING:
            if self.order.wing_qty > 0 and self.order.customer_name:
                # Have both wings and name
                self.state = DialogueState.ASKING_MAIN_ITEM
            elif self.order.wing_qty > 0:
                # Have wings, need name
                self.state = DialogueState.ASKING_NAME
            elif self.order.customer_name:
                # Have name, need wings
                self.state = DialogueState.ASKING_MAIN_ITEM
        
        elif self.state == DialogueState.ASKING_NAME:
            # Waiting for name - transition happens when name extracted
            if self.order.wing_qty > 0 and self.order.customer_name:
                self.state = DialogueState.ASKING_MAIN_ITEM
        
        elif self.state == DialogueState.ASKING_MAIN_ITEM:
            if self.order.wing_type:
                if self.order.wing_qty >= 6 and not self.order.combo_decided:
                    self.state = DialogueState.ASKING_COMBO
                else:
                    self.state = DialogueState.ASKING_FLAVOR
        
        elif self.state == DialogueState.ASKING_COMBO:
            if self.order.combo_decided:
                if self.order.is_combo:
                    self.state = DialogueState.ASKING_DRINK
                else:
                    self.state = DialogueState.ASKING_FLAVOR if not self.order.flavors else DialogueState.CONFIRMING
        
        elif self.state == DialogueState.ASKING_FLAVOR:
            if self.order.flavors:
                if self.order.wing_qty >= 6 and not self.order.combo_decided:
                    self.state = DialogueState.ASKING_COMBO
                else:
                    self.state = DialogueState.CONFIRMING
        
        elif self.state == DialogueState.ASKING_DRINK:
            if self.order.drink:
                self.state = DialogueState.ASKING_SIDES
        
        elif self.state == DialogueState.ASKING_SIDES:
            if self.order.side:
                self.state = DialogueState.ASKING_DIP
        
        elif self.state == DialogueState.ASKING_DIP:
            if self.order.dip:
                self.state = DialogueState.CONFIRMING
        
        elif self.state == DialogueState.MODIFYING:
            self.state = DialogueState.ASKING_MAIN_ITEM
    
    def _get_state_response(self) -> str:
        """Get hardcoded response based on state - faster and more reliable"""
        name = self.order.customer_name or ""
        
        if self.state == DialogueState.GREETING:
            if self.order.wing_qty > 0 and not name:
                return f"Gotcha, {self.order.wing_qty} wings! What's your name?"
            return "Hey! Welcome to Wingstop! I'm Tasha. What's your name?"
        
        elif self.state == DialogueState.ASKING_NAME:
            return f"Gotcha! And your name?"
        
        elif self.state == DialogueState.ASKING_MAIN_ITEM:
            return f"{self.order.wing_qty} wings, gotcha! Bone-in or boneless?"
        
        elif self.state == DialogueState.ASKING_FLAVOR:
            name_part = f"{name}, " if name else ""
            return f"{name_part}{self.order.wing_type}, nice! What flavors? Lemon Pepper's popular!"
        
        elif self.state == DialogueState.ASKING_COMBO:
            name_part = f"{name}, " if name else ""
            return f"{name_part}want to make that a combo with fries and a drink?"
        
        elif self.state == DialogueState.ASKING_DRINK:
            return "What to drink? Coke, Diet, Sprite, lemonade?"
        
        elif self.state == DialogueState.ASKING_SIDES:
            return "Seasoned fries or veggie sticks?"
        
        elif self.state == DialogueState.ASKING_DIP:
            return "What dip? Ranch, blue cheese, or honey mustard?"
        
        elif self.state == DialogueState.CONFIRMING:
            price = self._calculate_price()
            summary = self._get_order_summary_text()
            return f"So that's {summary}. Total is ${price:.2f}. Look right?"
        
        elif self.state == DialogueState.COMPLETED:
            price = self._calculate_price()
            return f"Perfect! Ready in 15-20 mins, {name}. Total ${price:.2f}. See you then!"
        
        return ""  # Let LLM handle other cases
    
    def _get_suggestion_response(self) -> str:
        """Get response when user asks for suggestions"""
        name = self.order.customer_name or ""
        name_part = f"{name}, " if name else ""
        
        if self.state == DialogueState.ASKING_FLAVOR:
            return f"{name_part}Lemon Pepper's our #1 seller! Or try Atomic if you like spicy."
        elif self.state == DialogueState.ASKING_MAIN_ITEM:
            return f"{name_part}Can't go wrong with boneless! Easier to eat."
        elif self.state == DialogueState.ASKING_COMBO:
            return f"{name_part}Combo's a good deal - saves you about $3!"
        elif self.state == DialogueState.ASKING_DRINK:
            return f"{name_part}Our lemonade is fresh-squeezed!"
        else:
            return f"{name_part}Lemon Pepper's crazy popular, you gotta try it!"
    
    def _get_llm_response(self, user_text: str) -> str:
        """Get response from LLM"""
        try:
            system_prompt = self._get_system_prompt()
            
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history[-4:])  # Keep last 2 turns
            messages.append({"role": "user", "content": user_text})
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            response_text = response.choices[0].message.content or ""
            
            # Update history
            self.conversation_history.append({"role": "user", "content": user_text})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return response_text
            
        except Exception as e:
            print(f"[Agent] LLM error: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """Fallback response"""
        fallbacks = {
            DialogueState.GREETING: "Hey! What's your name?",
            DialogueState.ASKING_NAME: "What's your name for the order?",
            DialogueState.ASKING_MAIN_ITEM: "How many wings?",
            DialogueState.ASKING_FLAVOR: "What flavors?",
            DialogueState.ASKING_COMBO: "Make it a combo?",
            DialogueState.ASKING_DRINK: "What to drink?",
            DialogueState.ASKING_SIDES: "Fries or veggie sticks?",
            DialogueState.ASKING_DIP: "What dip?",
            DialogueState.CONFIRMING: f"Total is ${self._calculate_price():.2f}. Look right?",
            DialogueState.COMPLETED: f"See you in 15-20 mins, {self.order.customer_name}!",
        }
        return fallbacks.get(self.state, "What was that?")
    
    def _handle_repeat_order(self) -> str:
        """Handle repeat order request"""
        summary = self._get_order_summary_text()
        if summary == "(nothing yet)":
            return "You haven't ordered anything yet. What can I getcha?"
        return f"You got: {summary}."
    
    def _generate_confirmation(self) -> str:
        """Generate confirmation message"""
        summary = self._get_order_summary_text()
        price = self._calculate_price()
        return f"So that's {summary}. Total is ${price:.2f}. Look right?"
    
    def _calculate_price(self) -> float:
        """Calculate order price"""
        total = 0.0
        if self.order.has_wings():
            total += self.order.wing_qty * self.wing_price
        if self.order.drink:
            total += 3.49 if self.order.drink_size == "32oz" else 2.49
        if self.order.side:
            total += 4.49 if "cheese" in self.order.side else 3.49
        if self.order.dip:
            total += 0.99
        if self.order.is_combo:
            total -= self.combo_savings
        return max(total, 0)
    
    def _clean_response(self, text: str) -> str:
        """Clean up response"""
        if not text:
            return self._get_fallback_response()
        
        forbidden = ["as an ai", "i apologize", "i'm sorry", "unfortunately", 
                     "however", "furthermore", "moreover"]
        text_lower = text.lower()
        for phrase in forbidden:
            if phrase in text_lower:
                return self._get_fallback_response()
        
        return text.strip().strip('"').strip("'")
    
    def _get_order_data(self) -> Dict:
        """Get order data"""
        items = self.order.to_items_list()
        print(f"[Agent] Order data: {len(items)} items, state={self.state.value}")
        return {
            "items": items,
            "state": self.state.value,
            "order_complete": self.state == DialogueState.COMPLETED,
            "has_wings": self.order.has_wings(),
            "customer_name": self.order.customer_name,
            "total_price": self._calculate_price()
        }
    
    def get_order_summary(self) -> Dict:
        """Get complete summary"""
        return {
            "state": self.state.value,
            "order_text": self._get_order_summary_text(),
            "items": self.order.to_items_list(),
            "customer_name": self.order.customer_name,
            "wing_qty": self.order.wing_qty,
            "wing_type": self.order.wing_type,
            "flavors": self.order.flavors,
            "is_combo": self.order.is_combo,
            "total_price": self._calculate_price()
        }
    
    def reset(self):
        """Reset agent"""
        self.state = DialogueState.GREETING
        self.order = CurrentOrder()
        self.conversation_history = []
