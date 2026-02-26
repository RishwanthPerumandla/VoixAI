#!/usr/bin/env python3
"""Test dashboard with live data"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orders.concurrent_manager import ConcurrentSessionManager


async def test():
    manager = ConcurrentSessionManager()
    await manager.start()
    
    # Create a session
    session = manager.create_session('ws_test', 'Rishi')
    
    # Simulate some messages
    agent = manager.agents[session.session_id]
    await agent.process('10 wings', session.session_id)
    await agent.process('classic', session.session_id)
    await agent.process('lemon pepper', session.session_id)
    
    # Get dashboard data
    data = manager.get_dashboard_data()
    print('='*60)
    print('DASHBOARD TEST')
    print('='*60)
    print(f"Stats: {data['stats']}")
    print(f"Active Sessions: {len(data['active_sessions'])}")
    for s in data['active_sessions']:
        print(f"  - {s['customer']}: ${s['total']} ({s['items']} items)")
    print('='*60)
    
    await manager.stop()


if __name__ == "__main__":
    asyncio.run(test())
