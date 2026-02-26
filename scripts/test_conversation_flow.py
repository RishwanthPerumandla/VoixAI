#!/usr/bin/env python3
"""Test full conversation flow"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orders.order_agent import OrderCentricAgent

async def test():
    agent = OrderCentricAgent()
    session_id = "test-session"
    
    conversation = [
        ("user", "10 wings"),
        ("user", "lemon pepper"),
        ("user", "nothing"),
    ]
    
    print("Full Conversation Test:")
    print("="*60)
    
    for speaker, message in conversation:
        print(f"\nCustomer: {message}")
        response = await agent.process(message, session_id)
        print(f"Agent: {response[:100]}...")
    
    print("\n" + "="*60)
    print("Conversation completed successfully!")

if __name__ == "__main__":
    asyncio.run(test())
