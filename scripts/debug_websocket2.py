#!/usr/bin/env python3
"""Debug WebSocket message flow - no timeout"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

print("Testing WebSocket message flow...")
print("="*60)

try:
    with client.websocket_connect('/ws') as ws:
        # Receive welcome
        msg = ws.receive_json()
        print(f"1. Server welcome: {msg['type']}")
        session_id = msg['session_id']
        
        # Send text message as JSON (like frontend does)
        print("\n2. Sending JSON: {type: 'text', content: '10 wings'}")
        ws.send_json({'type': 'text', 'content': '10 wings'})
        
        # Receive bot response
        print("3. Waiting for bot_response...")
        resp = ws.receive_json()
        print(f"   Type: {resp.get('type')}")
        print(f"   Content: {resp.get('content', 'N/A')[:80]}...")
        
        # Receive order status
        print("4. Waiting for order_status...")
        status = ws.receive_json()
        print(f"   Type: {status.get('type')}")
        print(f"   Data: {status.get('data')}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
