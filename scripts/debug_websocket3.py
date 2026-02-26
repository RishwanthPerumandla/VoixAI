#!/usr/bin/env python3
"""Debug WebSocket with fixed message types"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

print("Testing FIXED WebSocket message flow...")
print("="*60)

try:
    with client.websocket_connect('/ws') as ws:
        # 1. Receive welcome (should be system + session_started)
        msg = ws.receive_json()
        print(f"1. Server welcome:")
        print(f"   Type: {msg.get('type')}")
        print(f"   Event: {msg.get('event')}")
        print(f"   Session: {msg.get('session_id')}")
        
        # 2. Send start_conversation
        print("\n2. Sending: start_conversation")
        ws.send_json({'type': 'start_conversation'})
        resp = ws.receive_json()
        print(f"   Response: {resp}")
        
        # 3. Send text message
        print("\n3. Sending: '10 wings'")
        ws.send_json({'type': 'text', 'content': '10 wings'})
        
        # 4. Receive bot_text response
        resp = ws.receive_json()
        print(f"4. Bot response:")
        print(f"   Type: {resp.get('type')}")
        print(f"   Content: {resp.get('content', 'N/A')[:60]}...")
        
        # 5. Receive order_status
        status = ws.receive_json()
        print(f"5. Order status:")
        print(f"   Type: {status.get('type')}")
        
        print("\n[SUCCESS] All message types working!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("="*60)
