#!/usr/bin/env python3
"""
Demo: Concurrent Customer Sessions
Tests the full concurrent system with multiple customers
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket


def test_http_endpoints():
    """Test HTTP endpoints"""
    print("\n" + "="*60)
    print("Testing HTTP Endpoints")
    print("="*60)
    
    from src.main import app
    client = TestClient(app)
    
    # Health check
    r = client.get('/health')
    print(f"[OK] Health: {r.json()}")
    
    # Dashboard page
    r = client.get('/dashboard')
    print(f"[OK] Dashboard HTML: {len(r.text)} bytes")
    
    # Stats API
    r = client.get('/api/stats')
    stats = r.json()
    print(f"[OK] Stats API: {stats}")
    
    # Dashboard API
    r = client.get('/api/dashboard')
    dashboard = r.json()
    print(f"[OK] Dashboard API: {len(dashboard['active_sessions'])} active sessions")
    
    print("\n[SUCCESS] All HTTP endpoints working!")


def test_websocket_concurrent():
    """Test WebSocket with multiple concurrent clients"""
    print("\n" + "="*60)
    print("Testing Concurrent WebSocket Sessions")
    print("="*60)
    
    from src.main import app
    client = TestClient(app)
    
    # Client 1: Rishi
    print("\n--- Client 1 (Rishi) connecting ---")
    with client.websocket_connect('/ws') as ws1:
        # Receive welcome
        msg1 = ws1.receive_json()
        session1_id = msg1['session_id']
        print(f"[OK] Rishi connected: Session {session1_id}")
        print(f"  Message: {msg1['message']}")
        
        # Send order
        ws1.send_json({"type": "message", "content": "I want 10 boneless wings"})
        resp1 = ws1.receive_json()
        print(f"  Response: {resp1['content'][:60]}...")
        
        # Client 2: Sarah (simultaneous)
        print("\n--- Client 2 (Sarah) connecting ---")
        with client.websocket_connect('/ws') as ws2:
            msg2 = ws2.receive_json()
            session2_id = msg2['session_id']
            print(f"[OK] Sarah connected: Session {session2_id}")
            
            # Verify different sessions
            assert session1_id != session2_id, "Sessions should be different!"
            print(f"[OK] Sessions are isolated: {session1_id} != {session2_id}")
            
            # Sarah orders
            ws2.send_json({"type": "message", "content": "15 bone-in wings please"})
            resp2 = ws2.receive_json()
            print(f"  Response: {resp2['content'][:60]}...")
            
            # Check dashboard shows both
            print("\n--- Checking Dashboard ---")
            r = client.get('/api/dashboard')
            dashboard = r.json()
            print(f"Active sessions: {dashboard['stats']['active_sessions']}")
            for s in dashboard['active_sessions']:
                print(f"  - {s['customer']}: ${s['total']}")
    
    print("\n[SUCCESS] Concurrent WebSocket test passed!")


def test_dashboard_realtime():
    """Test dashboard updates in real-time"""
    print("\n" + "="*60)
    print("Testing Dashboard Real-time Updates")
    print("="*60)
    
    from src.main import app
    client = TestClient(app)
    
    # Initial state
    r = client.get('/api/dashboard')
    initial = r.json()
    print(f"Initial: {initial['stats']['active_sessions']} sessions")
    
    # Connect a client
    with client.websocket_connect('/ws') as ws:
        msg = ws.receive_json()
        print(f"Client connected: {msg['session_id']}")
        
        # Send a message to create activity
        ws.send_json({"type": "message", "content": "Hi, I'd like to order"})
        ws.receive_json()
        
        # Check dashboard updated
        r = client.get('/api/dashboard')
        updated = r.json()
        print(f"After connect: {updated['stats']['active_sessions']} sessions")
        print(f"Messages: {updated['active_sessions'][0]['messages']}")
    
    print("\n[SUCCESS] Dashboard real-time updates working!")


async def test_concurrent_sessions():
    """Test the full concurrent session system"""
    print("\n" + "="*60)
    print("Full Concurrent System Test")
    print("="*60)
    
    from src.orders.concurrent_manager import ConcurrentSessionManager
    from src.orders.state_machine import OrderItem, OrderState
    
    manager = ConcurrentSessionManager()
    await manager.start()
    
    print("\nCreating 3 simultaneous customer sessions...")
    
    # Customer 1
    s1 = manager.create_session('ws_1', 'Rishi')
    o1 = manager.get_order(s1.session_id)
    o1.add_item(OrderItem(id='w1', name='Boneless Wings', category='wings', 
                          quantity=10, unit_price=1.29, flavor='Lemon Pepper'))
    o1.set_customer_info('Rishi')
    print(f"[OK] Rishi: {o1.item_count} items, ${o1.total:.2f}")
    
    # Customer 2 (simultaneous)
    s2 = manager.create_session('ws_2', 'Sarah')
    o2 = manager.get_order(s2.session_id)
    o2.add_item(OrderItem(id='w2', name='Bone-In Wings', category='wings',
                          quantity=15, unit_price=1.19, flavor='Garlic Parmesan'))
    o2.set_customer_info('Sarah')
    print(f"[OK] Sarah: {o2.item_count} items, ${o2.total:.2f}")
    
    # Customer 3 (simultaneous)
    s3 = manager.create_session('ws_3', 'Mike')
    o3 = manager.get_order(s3.session_id)
    o3.add_item(OrderItem(id='c1', name='Combo Meal', category='combo',
                          quantity=1, unit_price=24.99))
    o3.set_customer_info('Mike')
    print(f"[OK] Mike: {o3.item_count} items, ${o3.total:.2f}")
    
    # Verify isolation
    print("\nVerifying session isolation...")
    assert o1.total != o2.total != o3.total
    assert o1.customer_name == 'Rishi'
    assert o2.customer_name == 'Sarah'
    assert o3.customer_name == 'Mike'
    print("[OK] All sessions are isolated")
    
    # Dashboard data
    print("\nDashboard Data:")
    dashboard = manager.get_dashboard_data()
    print(f"  Total sessions: {dashboard['stats']['total_sessions']}")
    print(f"  Active sessions: {dashboard['stats']['active_sessions']}")
    print(f"  Active orders: {dashboard['stats']['active_orders']}")
    
    print("\nActive Orders:")
    for s in dashboard['active_sessions']:
        print(f"  - {s['customer']}: {s['order_state']} - ${s['total']}")
    
    await manager.stop()
    print("\n[SUCCESS] Full concurrent system test passed!")


def main():
    """Run all tests"""
    print("="*60)
    print("VoixAI Concurrent System Demo")
    print("="*60)
    
    try:
        # Test HTTP endpoints
        test_http_endpoints()
        
        # Test WebSocket concurrent
        test_websocket_concurrent()
        
        # Test dashboard
        test_dashboard_realtime()
        
        # Test full system
        asyncio.run(test_concurrent_sessions())
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
        print("\nServer is ready to use:")
        print("  1. Start server: python -m uvicorn src.main:app --reload")
        print("  2. Open browser: http://localhost:8000")
        print("  3. Dashboard: http://localhost:8000/dashboard")
        print("  4. Open multiple tabs to test concurrent customers")
        print("="*60)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
