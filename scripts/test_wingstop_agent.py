#!/usr/bin/env python3
"""Test Wingstop agent with complete menu"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.wingstop_agent import WingstopAgent


async def test_complete_flow():
    agent = WingstopAgent()
    session_id = "test-123"
    
    print("="*60)
    print("Wingstop Complete Menu Agent Test")
    print("="*60)
    
    # Test 1: Just quantity
    print("\n1. Customer: '10 wings'")
    resp = await agent.process("10 wings", session_id)
    print(f"   Tasha: {resp}")
    
    # Test 2: Specify type
    print("\n2. Customer: 'boneless'")
    resp = await agent.process("boneless", session_id)
    print(f"   Tasha: {resp}")
    
    # Test 3: Flavor
    print("\n3. Customer: 'lemon pepper'")
    resp = await agent.process("lemon pepper", session_id)
    print(f"   Tasha: {resp}")
    
    # Test 4: Done
    print("\n4. Customer: 'that's all'")
    resp = await agent.process("that's all", session_id)
    print(f"   Tasha: {resp}")
    
    # Test 5: Name
    print("\n5. Customer: 'name is Rishi'")
    resp = await agent.process("name is Rishi", session_id)
    print(f"   Tasha: {resp}")
    
    # Check status
    print("\n" + "="*60)
    status = agent.get_order_status(session_id)
    print(f"Order: {status['items']} items, ${status['total']:.2f}")
    print(f"Customer: {status['customer']}")
    print(f"Complete: {status['complete']}")
    print("="*60)


async def test_natural_flow():
    print("\n" + "="*60)
    print("Natural Conversation Flow Test")
    print("="*60)
    
    agent = WingstopAgent()
    session_id = "test-456"
    
    conversation = [
        "I'd like to order some wings",
        "boneless please",
        "10 piece",
        "garlic parmesan",
        "also some seasoned fries",
        "and a ranch dip",
        "that's all",
        "it's for Sarah",
        "yes confirm"
    ]
    
    for msg in conversation:
        print(f"\nCustomer: {msg}")
        resp = await agent.process(msg, session_id)
        print(f"Tasha: {resp}")
    
    print("\n" + "="*60)
    status = agent.get_order_status(session_id)
    print(f"Final Order: ${status['total']:.2f}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_complete_flow())
    asyncio.run(test_natural_flow())
