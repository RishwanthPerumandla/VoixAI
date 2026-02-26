#!/usr/bin/env python3
"""Test the intelligent agent without state machines"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.intelligent_order_agent import IntelligentOrderAgent


async def test():
    agent = IntelligentOrderAgent()
    session_id = "test-session"
    
    conversation = [
        "10 wings",
        "lemon pepper",
        "nothing",
        "name is Rishi",
        "yes confirm"
    ]
    
    print("="*60)
    print("Intelligent Agent Test - Natural Conversation")
    print("="*60)
    
    for message in conversation:
        print(f"\nCustomer: {message}")
        response = await agent.process(message, session_id)
        print(f"Tasha: {response}")
    
    print("\n" + "="*60)
    print("Final Order Status:")
    status = agent.get_order_status(session_id)
    print(f"  Customer: {status.get('customer')}")
    print(f"  Items: {status.get('item_count')}")
    print(f"  Total: ${status.get('total', 0):.2f}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test())
