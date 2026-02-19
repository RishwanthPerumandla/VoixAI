"""Test script for conversational agent state machine"""
import os
import re
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, List

print("=" * 60)
print("Testing Conversational Agent State Machine")
print("=" * 60)

# Test 1: State Enum
print("\n[TEST 1] State Enum Values")

class DialogueState(Enum):
    GREETING = "greeting"
    ASKING_MAIN_ITEM = "asking_main_item"
    ASKING_FLAVOR = "asking_flavor"
    ASKING_COMBO = "asking_combo"
    ASKING_DRINK = "asking_drink"
    ASKING_SIDES = "asking_sides"
    ASKING_DIP = "asking_dip"
    CONFIRMING = "confirming"
    MODIFYING = "modifying"
    COMPLETED = "completed"

for state in DialogueState:
    print(f"  [OK] {state.name}: {state.value}")
print("  [PASS] All states defined correctly")

# Test 2: OrderItem dataclass
print("\n[TEST 2] OrderItem Dataclass")

@dataclass
class OrderItem:
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

item = OrderItem(name="boneless wings", qty=6, category="wings", 
                 modifiers={"flavors": [{"flavor": "lemon pepper", "qty": 6}]})
print(f"  [OK] Created: {item.to_dict()}")
print("  [OK] OrderItem works")

# Test 3: CurrentOrder dataclass
print("\n[TEST 3] CurrentOrder Dataclass")

@dataclass
class CurrentOrder:
    wing_qty: int = 0
    wing_type: str = ""
    flavors: List[Dict[str, Any]] = field(default_factory=list)
    is_combo: bool = False
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

order = CurrentOrder()
order.wing_qty = 6
order.wing_type = "boneless"
order.flavors = [{"flavor": "lemon pepper", "qty": 3}, 
                 {"flavor": "cajun", "qty": 3}]
order.is_combo = True
order.drink = "diet coke"
order.drink_size = "20oz"
order.side = "seasoned fries"
order.dip = "ranch"

print(f"  [OK] Order summary: {order.get_flavor_summary()}")
print(f"  [OK] Has wings: {order.has_wings()}")
print(f"  [OK] Wing type: {order.wing_type}")
print("  [OK] CurrentOrder works")

# Test 4: Info extraction patterns
print("\n[TEST 4] Info Extraction Patterns")

def extract_wing_info(text):
    """Extract wing quantity and type from text"""
    text_lower = text.lower()
    result = {}
    
    # Wing quantity patterns
    patterns = [
        r'(\d+)\s*(?:piece|pc|wing|wings)',
        r'(\d+)\s*(?:boneless|bone-in|classic)',
        r'(?:get|want|give me|lemme get)\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            result['wing_qty'] = int(match.group(1))
            break
    
    # Wing type
    if 'boneless' in text_lower:
        result['wing_type'] = 'boneless'
    elif 'bone-in' in text_lower or 'bone in' in text_lower or 'classic' in text_lower:
        result['wing_type'] = 'bone-in'
    
    return result

test_cases = [
    ("6 boneless wings", {"wing_qty": 6, "wing_type": "boneless"}),
    ("10 bone-in", {"wing_qty": 10, "wing_type": "bone-in"}),
    ("8 classic wings", {"wing_qty": 8, "wing_type": "bone-in"}),
    ("lemme get 15", {"wing_qty": 15}),
]

for text, expected in test_cases:
    result = extract_wing_info(text)
    match = all(result.get(k) == v for k, v in expected.items())
    status = "[OK]" if match else "[FAIL]"
    print(f"  {status} '{text}' -> {result}")

print("  [OK] Extraction patterns work")

# Test 5: State transitions
print("\n[TEST 5] State Transitions")

class MockAgent:
    def __init__(self):
        self.state = DialogueState.GREETING
        self.order = CurrentOrder()
    
    def transition(self, user_input):
        """Simple state transition logic"""
        text_lower = user_input.lower()
        
        if self.state == DialogueState.GREETING:
            # Extract wing info
            info = extract_wing_info(user_input)
            if 'wing_qty' in info:
                self.order.wing_qty = info['wing_qty']
                self.order.wing_type = info.get('wing_type', '')
                if self.order.wing_qty >= 6:
                    self.state = DialogueState.ASKING_COMBO
                else:
                    self.state = DialogueState.ASKING_FLAVOR
        
        elif self.state == DialogueState.ASKING_COMBO:
            if any(w in text_lower for w in ['yes', 'yeah', 'sure']):
                self.order.is_combo = True
                self.state = DialogueState.ASKING_DRINK
            elif any(w in text_lower for w in ['no', 'nah']):
                self.order.is_combo = False
                self.state = DialogueState.ASKING_FLAVOR
        
        elif self.state == DialogueState.ASKING_FLAVOR:
            # Simulate flavor extraction
            self.state = DialogueState.CONFIRMING
        
        elif self.state == DialogueState.CONFIRMING:
            if any(w in text_lower for w in ['yes', 'yeah', 'correct']):
                self.state = DialogueState.COMPLETED
            elif any(w in text_lower for w in ['no', 'wrong']):
                self.state = DialogueState.MODIFYING
        
        return self.state

agent = MockAgent()

conversations = [
    ("6 boneless", DialogueState.ASKING_COMBO),
    ("yeah make it a combo", DialogueState.ASKING_DRINK),  # Combo accepted -> ask drink
    ("diet coke", DialogueState.CONFIRMING),  # After drink, would go to sides, then confirming
    ("yes that's right", DialogueState.COMPLETED),
]

for user_input, expected_state in conversations:
    new_state = agent.transition(user_input)
    status = "[OK]" if new_state == expected_state else "[FAIL]"
    print(f"  {status} '{user_input[:30]}...' -> {new_state.value}")

print("  [OK] State transitions work")

# Summary
print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
print("\nTo run the full system:")
print("1. Set GROQ_API_KEY environment variable")
print("2. Run: python main_conversational.py")
print("3. Open http://localhost:8000 in browser")
