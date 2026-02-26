#!/usr/bin/env python3
"""Test the true LLM-powered cashier"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.cashier_agent import WingstopCashier


async def test():
    cashier = WingstopCashier()
    session_id = "test-1"
    
    conversation = [
        "Hey, I'd like to place an order",
        "Rishi",
        "10 wings",
        "classic",
        "Lemon Pepper",
        "That's all",
        "Yes"
    ]
    
    print("="*60)
    print("Wingstop Cashier - LLM Powered Test")
    print("="*60)
    
    for msg in conversation:
        print(f"\nCustomer: {msg}")
        resp = await cashier.process(msg, session_id)
        print(f"Tasha: {resp}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test())
