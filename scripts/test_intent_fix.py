#!/usr/bin/env python3
"""Test intent parsing fix for 'nothing', 'that's all' etc."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orders.order_agent import OrderUnderstandingEngine
from src.orders.state_machine import Order, OrderItem

# Create engine
engine = OrderUnderstandingEngine()

# Create a test order with items
class MockOrder:
    def __init__(self):
        self.items = []
        self.is_empty = True
        
    def add_item(self, item):
        self.items.append(item)
        self.is_empty = False

order = MockOrder()
order.add_item(OrderItem(id='w1', name='Bone-In Wings', category='wings', quantity=10, unit_price=1.29, flavor='Lemon Pepper'))

# Test phrases
test_phrases = [
    ("nothing", "should review"),
    ("that's all", "should review"),
    ("no more", "should review"),
    ("i'm good", "should review"),
    ("done", "should review"),
    ("finished", "should review"),
    ("complete", "should review"),
    ("that is it", "should review"),
    ("no thanks", "should review"),
    ("nope", "should review"),
    ("add fries", "should add item"),
    ("i want 10 wings", "should add item"),
]

print("Testing Intent Classification:")
print("="*60)

for phrase, expected in test_phrases:
    intent = engine.parse(phrase, order)
    status = "OK" if intent.intent_type in ['review', 'add_item'] else "FAIL"
    print(f"'{phrase}' -> {intent.intent_type} [{status}]")

print("="*60)
