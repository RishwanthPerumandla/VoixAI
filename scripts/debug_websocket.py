#!/usr/bin/env python3
"""Debug WebSocket message flow"""

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
        print(f"   Session: {msg['session_id']}")
        print(f"   Message: {msg['message'][:50]}...")
        
        # Send text message (simple string)
        print("\n2. Sending: '10 wings'")
        ws.send_text('10 wings')
        
        # Try to receive response
        print("3. Waiting for response...")
        try:
            resp = ws.receive_json(timeout=10)
            print(f"   Response type: {resp.get('type')}")
            print(f"   Content: {resp.get('content', 'N/A')[:100]}...")
        except Exception as e:
            print(f"   ERROR receiving: {e}")
            
except Exception as e:
    print(f"Connection error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
