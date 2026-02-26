#!/usr/bin/env python3
"""Test simple intelligent agent"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.simple_intelligent_agent import SimpleIntelligentAgent


async def test():
    agent = SimpleIntelligentAgent()
    session_id = "test-session"
    
    conversation = [
        "10 wings",
        "lemon pepper", 
        "nothing",
        "name is Rishi",
        "yes confirm"
    ]
    
    print("="*60)
    print("Simple Intelligent Agent Test")
    print("="*60)
    
    for msg in conversation:
        print(f"\nCustomer: {msg}")
        resp = await agent.process(msg, session_id)
        print(f"Tasha: {resp}")
    
    print("\n" + "="*60)
    status = agent.get_order_status(session_id)
    print(f"Final: {status['item_count']} items, ${status['total']:.2f}")
    print(f"Customer: {status['customer']}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test())
