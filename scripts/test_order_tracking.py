#!/usr/bin/env python3
"""Test order tracking"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.cashier_agent import WingstopCashier


async def test():
    agent = WingstopCashier()
    session_id = 'test'
    
    print('Before:', agent.get_status(session_id))
    
    await agent.process('10 wings', session_id)
    print('After 10 wings:', agent.get_status(session_id))
    if session_id in agent.orders:
        print('  Items:', len(agent.orders[session_id].items))
        for item in agent.orders[session_id].items:
            print(f"    - {item}")
    
    await agent.process('classic', session_id)
    print('After classic:', agent.get_status(session_id))
    
    await agent.process('lemon pepper', session_id)
    print('After flavor:', agent.get_status(session_id))


if __name__ == "__main__":
    asyncio.run(test())
