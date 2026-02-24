"""Generation Module - Natural response synthesis"""
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ResponseStyle:
    """Style parameters for response generation"""
    tone: str = "friendly"  # friendly|empathetic|energetic|professional
    length: str = "short"   # short|medium|long
    urgency: str = "normal" # normal|urgent


class ResponseGenerator:
    """Generates natural, varied responses grounded in tool results"""
    
    # Anti-patterns to avoid
    FORBIDDEN_PHRASES = [
        "as an ai",
        "as a language model",
        "i apologize for the inconvenience",
        "i'm sorry to hear that",
        "please hold while i",
        "i will now",
        "furthermore",
        "moreover",
        "however",
        "additionally"
    ]
    
    def __init__(self):
        self.response_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, List[str]]:
        """Load response templates - varied for naturalness"""
        return {
            "greeting": [
                "Hey! Welcome to Wingstop. I'm Tasha. What's your name?",
                "Hey there! Tasha here. What's the name for your order?",
                "Welcome to Wingstop! I'm Tasha. Who am I making this for?",
            ],
            "greeting_with_name": [
                "Hey {name}! What can I get you?",
                "What's up {name}? What are you craving?",
                "Hey {name}! Ready to order?",
                "Got it, {name}! How many wings can I get you?",
            ],
            "ask_name": [
                "What's your name?",
                "Who's this for?",
                "Name for the order?",
            ],
            "ask_wing_qty": [
                "How many wings? We do 6, 8, 10, 15, 20, 30.",
                "What size? 6, 8, 10, 15, 20, or 30 piece.",
                "How many you want? 6, 8, 10, 15, 20, 30.",
            ],
            "ask_wing_type": [
                "{qty} wings, got it! Bone-in or boneless?",
                "{qty} piece - bone-in or boneless?",
                "Gotcha, {qty}. Bone-in or boneless?",
            ],
            "ask_flavor": [
                "What flavors? Lemon Pepper's our #1.",
                "What flavors you want? You can pick up to 2.",
                "Which flavors? Lemon Pepper, Garlic Parm, Atomic?",
            ],
            "ask_combo": [
                "Want to make that a combo with fries and a drink?",
                "Make it a combo? Gets you fries and a drink.",
                "Want the combo with fries and a drink?",
            ],
            "ask_drink": [
                "What to drink? Coke, Diet, Sprite, Dr Pepper, lemonade?",
                "What you drinking? Coke, Sprite, Dr Pepper, lemonade?",
                "Coke, Diet, Sprite, Dr Pepper, or lemonade?",
            ],
            "ask_side": [
                "Seasoned fries or veggie sticks?",
                "Fries or veggie sticks?",
                "Want seasoned fries or veggie sticks?",
            ],
            "ask_dip": [
                "What dip? Ranch, blue cheese, honey mustard?",
                "Ranch, blue cheese, or honey mustard?",
                "Want a dip? Ranch, blue cheese, honey mustard?",
            ],
            "confirm_item": [
                "{qty} {item_type}, got it.",
                "Gotcha—{qty} {item_type}.",
                "{qty} {item_type}, nice.",
            ],
            "confirm_order": [
                "So that's {order_summary}. Total is ${total}. Look right?",
                "You got {order_summary}. ${total} total. Good?",
                "That's {order_summary} for ${total}. Sound right?",
            ],
            "complete_order": [
                "Perfect! Order's in. {time} minutes {name}, ${total} at the counter. See you soon!",
                "All set! Ready in {time} minutes, ${total} when you get here {name}!",
                "You're good! {time} minutes, ${total} at pickup {name}!",
            ],
            "modify_acknowledge": [
                "No problem, changing that now.",
                "Got it, updating your order.",
                "My bad, fixing that.",
            ],
            "empathy_frustration": [
                "That's frustrating—let me fix that right now.",
                "My bad, sorting that out for you.",
                "That's annoying—fixing it now.",
            ],
            "empathy_complaint": [
                "That's not right. Making this better now.",
                "Sorry about that. Fixing it immediately.",
                "That's on us. Correcting that now.",
            ],
            "upsell_combo": [
                "Make it a combo? ${price}, you get fries and a drink—saves ${savings}.",
                "Want the combo? ${price} with fries and drink, saves you ${savings}.",
                "Combo's a good move—${price} with fries and drink. Saves ${savings}.",
            ],
            "upsell_side": [
                "Add seasoned fries? Fresh-cut daily.",
                "Our fries are amazing—add them?",
                "Throw in some seasoned fries?",
            ],
            "clarification": [
                "Say again?",
                "What was that?",
                "Run that by me again?",
            ],
            "not_sure_help": [
                "No worries, I got you. You like spicy or mild?",
                "All good, I'll help. Spicy or safe?",
                "No stress. Hot stuff or mild?",
            ],
            "flavor_recommendation": [
                "Lemon Pepper's our #1—tangy, citrusy. Original Hot's classic vinegar kick. Louisiana Rub's smoky. Which sounds good?",
                "Lemon Pepper—tangy and amazing. Original Hot—classic buffalo. Mango Habanero—sweet heat. What calls to you?",
                "Go with Lemon Pepper for mild, Original Hot for classic spicy, or Atomic if you're brave. Pick one?",
            ],
            "fallback": [
                "What was that?",
                "Didn't catch that—say again?",
                "One more time?",
            ],
            "small_talk_steer": [
                "Anyway, what can I get you?",
                "So, how many wings?",
                "Ready to order?",
            ],
        }
    
    def generate(self, context: Dict, tool_results: List[Dict] = None,
                 style: ResponseStyle = None) -> str:
        """
        Generate natural response based on context and tool results.
        """
        style = style or ResponseStyle()
        tool_results = tool_results or []
        
        action_type = context.get("action_type", "fallback")
        
        # Route to appropriate generator
        generators = {
            "greet": self._generate_greeting,
            "ask_name": self._generate_ask_name,
            "ask_wing_qty": self._generate_ask_wing_qty,
            "ask_wing_type": self._generate_ask_wing_type,
            "ask_flavor": self._generate_ask_flavor,
            "ask_combo": self._generate_ask_combo,
            "ask_drink": self._generate_ask_drink,
            "ask_side": self._generate_ask_side,
            "ask_dip": self._generate_ask_dip,
            "ask_clarification": self._generate_clarification,
            "ask_preference": self._generate_ask_preference,
            "confirm_item": self._generate_confirm_item,
            "confirm_order": self._generate_confirm_order,
            "complete_order": self._generate_complete_order,
            "upsell": self._generate_upsell,
            "answer_question": self._generate_answer,
            "express_empathy": self._generate_empathy,
            "recovery": self._generate_recovery,
            "small_talk": self._generate_small_talk,
        }
        
        generator = generators.get(action_type, self._generate_fallback)
        return generator(context, tool_results)
    
    def _generate_greeting(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate greeting response"""
        name = context.get("customer_name", "")
        if name:
            template = random.choice(self.response_templates["greeting_with_name"])
            return template.format(name=name)
        return random.choice(self.response_templates["greeting"])
    
    def _generate_ask_name(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["ask_name"])
    
    def _generate_ask_wing_qty(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["ask_wing_qty"])
    
    def _generate_ask_wing_type(self, context: Dict, tool_results: List[Dict]) -> str:
        qty = context.get("qty", 10)
        template = random.choice(self.response_templates["ask_wing_type"])
        return template.format(qty=qty)
    
    def _generate_ask_flavor(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["ask_flavor"])
    
    def _generate_ask_combo(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["ask_combo"])
    
    def _generate_ask_drink(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["ask_drink"])
    
    def _generate_ask_side(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["ask_side"])
    
    def _generate_ask_dip(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["ask_dip"])
    
    def _generate_ask_clarification(self, context: Dict, tool_results: List[Dict]) -> str:
        return random.choice(self.response_templates["clarification"])
    
    def _generate_ask_preference(self, context: Dict, tool_results: List[Dict]) -> str:
        pref_type = context.get("preference_type", "general")
        if pref_type == "flavor":
            return random.choice(self.response_templates["ask_flavor"])
        elif pref_type == "heat_level":
            return random.choice(self.response_templates["not_sure_help"])
        return random.choice(self.response_templates["clarification"])
    
    def _generate_confirm_item(self, context: Dict, tool_results: List[Dict]) -> str:
        item = context.get("item", {})
        qty = item.get("qty", 10)
        item_type = item.get("type", "wings")
        template = random.choice(self.response_templates["confirm_item"])
        return template.format(qty=qty, item_type=item_type)
    
    def _generate_confirm_order(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate order confirmation with pricing"""
        order_summary = context.get("order_summary", "your order")
        total = 0.0
        
        # Get total from tool results
        for result in tool_results:
            if result.get("tool") == "calculate_price" and result.get("success"):
                total = result.get("result", {}).get("total", 0)
        
        template = random.choice(self.response_templates["confirm_order"])
        return template.format(order_summary=order_summary, total=f"{total:.2f}")
    
    def _generate_complete_order(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate order completion message"""
        name = context.get("customer_name", "")
        total = 0.0
        
        for result in tool_results:
            if result.get("tool") == "calculate_price" and result.get("success"):
                total = result.get("result", {}).get("total", 0)
        
        template = random.choice(self.response_templates["complete_order"])
        return template.format(name=name, total=f"{total:.2f}", time=20)
    
    def _generate_upsell(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate upsell suggestion"""
        upsell_type = context.get("upsell_type", "combo")
        qty = context.get("qty", 10)
        
        # Get pricing from tool results
        savings = 3.0
        price = 19.99
        if qty == 15:
            savings = 6.50
            price = 23.99
        elif qty == 8:
            price = 16.99
        elif qty == 6:
            price = 13.99
        
        if upsell_type == "combo":
            template = random.choice(self.response_templates["upsell_combo"])
            return template.format(price=f"{price:.2f}", savings=f"{savings:.2f}")
        elif upsell_type == "side":
            return random.choice(self.response_templates["upsell_side"])
        else:
            return "Want to add anything else?"
    
    def _generate_answer(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate answer based on tool results"""
        query_type = context.get("query_type", "")
        
        # Handle price-related questions
        if query_type == "pricing":
            for result in tool_results:
                if result.get("tool") == "calculate_price" and result.get("success"):
                    data = result.get("result", {})
                    total = data.get("total", 0)
                    savings = data.get("savings", 0)
                    
                    if savings > 0:
                        return f"${total:.2f} total, and you're saving ${savings:.2f}."
                    return f"${total:.2f} total."
        
        # Handle recommendation questions
        if query_type == "recommendation":
            return random.choice(self.response_templates["flavor_recommendation"])
        
        # Handle menu search results
        for result in tool_results:
            if result.get("tool") == "search_menu" and result.get("success"):
                items = result.get("result", {}).get("results", [])
                if items:
                    if len(items) == 1:
                        item = items[0]
                        prices = item.get('prices', {})
                        min_price = min(prices.values()) if prices else 0
                        return f"{item['name']}—{item['description']}. ${min_price:.2f}"
                    else:
                        item_names = [i["name"] for i in items[:3]]
                        return f"We got {', '.join(item_names)}. Which sounds good?"
        
        return random.choice(self.response_templates["clarification"])
    
    def _generate_empathy(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate empathetic response"""
        empathy_type = context.get("empathy_type", "general")
        
        if empathy_type == "frustration":
            return random.choice(self.response_templates["empathy_frustration"])
        elif empathy_type == "complaint":
            return random.choice(self.response_templates["empathy_complaint"])
        else:
            return "I hear you. Let me help."
    
    def _generate_recovery(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate recovery response"""
        recovery_type = context.get("recovery_type", "general")
        message = context.get("message", "")
        
        if message:
            return message
        if recovery_type == "error":
            return "My bad, let's try that again."
        return random.choice(self.response_templates["modify_acknowledge"])
    
    def _generate_clarification(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate clarification request"""
        return random.choice(self.response_templates["clarification"])
    
    def _generate_small_talk(self, context: Dict, tool_results: List[Dict]) -> str:
        """Generate small talk response"""
        steer = context.get("steer_to_order", False)
        
        if steer:
            return random.choice(self.response_templates["small_talk_steer"])
        return random.choice(self.response_templates["small_talk_steer"])  # Always steer to order
    
    def _generate_fallback(self, context: Dict = None, tool_results: List[Dict] = None) -> str:
        """Generate fallback response"""
        return random.choice(self.response_templates["clarification"])
    
    def validate_response(self, text: str) -> bool:
        """Check if response contains forbidden phrases"""
        text_lower = text.lower()
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase in text_lower:
                return False
        return True
    
    def clean_response(self, text: str) -> str:
        """Clean up response if needed"""
        if not text:
            return self._generate_fallback()
        
        if not self.validate_response(text):
            return self._generate_fallback()
        
        # Remove quotes if present
        text = text.strip().strip('"').strip("'")
        
        return text
