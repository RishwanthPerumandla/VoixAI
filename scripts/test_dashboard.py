#!/usr/bin/env python3
"""Test dashboard API"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orders.concurrent_manager import ConcurrentSessionManager
from src.orders.state_machine import OrderItem


async def test():
    manager = ConcurrentSessionManager()
    await manager.start()
    
    # Create some test sessions
    s1 = manager.create_session('ws_1', 'Rishi')
    o1 = manager.get_order(s1.session_id)
    o1.add_item(OrderItem(id='w1', name='Boneless Wings', category='wings', quantity=10, unit_price=1.29, flavor='Lemon Pepper'))
    o1.set_customer_info('Rishi')
    
    s2 = manager.create_session('ws_2', 'Sarah')
    o2 = manager.get_order(s2.session_id)
    o2.add_item(OrderItem(id='w2', name='Bone-In Wings', category='wings', quantity=15, unit_price=1.19, flavor='Garlic Parmesan'))
    o2.set_customer_info('Sarah')
    
    # Get dashboard data
    dashboard = manager.get_dashboard_data()
    print('='*50)
    print('Dashboard Data:')
    print('='*50)
    print(f"Stats: {dashboard['stats']}")
    print(f"Active Sessions: {len(dashboard['active_sessions'])}")
    print()
    print('Active Orders:')
    for s in dashboard['active_sessions']:
        print(f"  - {s['customer']}: {s['order_state']} - ${s['total']}")
    
    await manager.stop()


if __name__ == "__main__":
    asyncio.run(test())
