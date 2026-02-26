"""
Concurrent WebSocket Handler
Supports multiple simultaneous customers (one per tab)
"""

import json
import asyncio
from typing import Dict, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from src.orders.concurrent_manager import ConcurrentSessionManager, WebSocketSessionHandler


class ConcurrentWebSocketEndpoint:
    """
    WebSocket endpoint that handles multiple concurrent customer sessions
    Each tab = one independent customer session
    """
    
    def __init__(self):
        self.session_manager = ConcurrentSessionManager(
            session_timeout=1800,  # 30 minutes
            cleanup_interval=60    # Cleanup every minute
        )
        self.ws_handler: Optional[WebSocketSessionHandler] = None
        self.is_running = False
    
    async def startup(self):
        """Initialize the session manager"""
        await self.session_manager.start()
        self.ws_handler = WebSocketSessionHandler(self.session_manager)
        self.is_running = True
        print("[WebSocket] Concurrent endpoint ready - Multiple customers supported")
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        await self.session_manager.stop()
        self.is_running = False
        print("[WebSocket] Concurrent endpoint stopped")
    
    async def handle_connection(self, websocket: WebSocket, client_info: Dict = None):
        """
        Handle a WebSocket connection
        Each connection gets its own isolated session
        """
        import uuid
        websocket_id = f"ws_{uuid.uuid4().hex[:12]}"
        
        await websocket.accept()
        print(f"[WebSocket] New connection: {websocket_id}")
        
        try:
            # Create session for this connection
            session = await self.ws_handler.connect(websocket_id, websocket)
            
            # Send welcome message (compatible with frontend)
            await websocket.send_json({
                "type": "system",
                "event": "session_started",
                "session_id": session.session_id,
                "message": "Welcome to Wingstop! What can I get for you today?"
            })
            
            # Message loop
            while True:
                try:
                    data = await websocket.receive()
                    
                    if data["type"] == "websocket.receive":
                        if "text" in data:
                            message = data["text"]
                            await self._handle_text_message(websocket, websocket_id, message)
                        elif "bytes" in data:
                            await self._handle_audio_data(websocket, websocket_id, data["bytes"])
                    
                    elif data["type"] == "websocket.disconnect":
                        break
                        
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    print(f"[WebSocket] Error handling message: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Sorry, I didn't catch that. Could you repeat?"
                    })
        
        except Exception as e:
            print(f"[WebSocket] Connection error: {e}")
        
        finally:
            await self.ws_handler.disconnect(websocket_id)
            print(f"[WebSocket] Connection closed: {websocket_id}")
    
    async def _handle_text_message(self, websocket: WebSocket, websocket_id: str, message: str):
        """Handle text message from client"""
        try:
            # Parse JSON if applicable
            try:
                data = json.loads(message)
                msg_type = data.get("type", "message")
                content = data.get("content", message)
            except json.JSONDecodeError:
                msg_type = "message"
                content = message
            
            # Get session for this websocket
            session = self.session_manager.get_session_by_websocket(websocket_id)
            
            # Handle different message types
            if msg_type == "start_conversation":
                # Already handled on connect, just confirm
                if session:
                    await websocket.send_json({
                        "type": "system",
                        "event": "session_started",
                        "session_id": session.session_id
                    })
            
            elif msg_type == "message" or msg_type == "text":
                response = await self.ws_handler.handle_message(websocket_id, content)
                
                # Send bot response (compatible with frontend)
                await websocket.send_json({
                    "type": "bot_text",
                    "content": response,
                    "latency_ms": 0
                })
                
                # Also send order status update
                await self._check_and_send_order_status(websocket, websocket_id)
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "get_status":
                await self._send_session_status(websocket, websocket_id)
            
            elif msg_type == "complete_order":
                await self._handle_order_completion(websocket, websocket_id)
            
            elif msg_type == "new_order":
                await self._handle_new_order_request(websocket, websocket_id)
            
        except Exception as e:
            print(f"[WebSocket] Text message error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Something went wrong. Please try again."
            })
    
    async def _handle_audio_data(self, websocket: WebSocket, websocket_id: str, audio_bytes: bytes):
        """Handle audio data"""
        await websocket.send_json({
            "type": "info",
            "message": "Voice input not yet implemented. Please type your order."
        })
    
    async def _check_and_send_order_status(self, websocket: WebSocket, websocket_id: str):
        """Check order status and send updates"""
        session = self.session_manager.get_session_by_websocket(websocket_id)
        if not session:
            return
        
        order = self.session_manager.get_order(session.session_id)
        if not order:
            return
        
        await websocket.send_json({
            "type": "order_status",
            "data": {
                "order_state": order.state.value,
                "item_count": order.item_count,
                "total": round(order.total, 2),
                "customer": order.customer_name
            }
        })
    
    async def _send_session_status(self, websocket: WebSocket, websocket_id: str):
        """Send full session status"""
        session = self.session_manager.get_session_by_websocket(websocket_id)
        if not session:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found"
            })
            return
        
        order = self.session_manager.get_order(session.session_id)
        
        await websocket.send_json({
            "type": "session_status",
            "data": {
                "session_id": session.session_id,
                "customer": session.customer_name,
                "status": session.status.value,
                "duration": int(session.duration_seconds),
                "messages": session.messages_count,
                "order": order.to_dict() if order else None
            }
        })
    
    async def _handle_order_completion(self, websocket: WebSocket, websocket_id: str):
        """Handle explicit order completion request"""
        session = self.session_manager.get_session_by_websocket(websocket_id)
        if not session:
            return
        
        order = self.session_manager.complete_order(session.session_id)
        
        if order:
            await websocket.send_json({
                "type": "order_completed",
                "message": f"Order #{order.id[:8]} completed! Thank you!",
                "order": {
                    "id": order.id[:8],
                    "total": round(order.total, 2),
                    "items": order.item_count
                }
            })
    
    async def _handle_new_order_request(self, websocket: WebSocket, websocket_id: str):
        """Handle request for new order (same tab)"""
        session = self.session_manager.get_session_by_websocket(websocket_id)
        if session:
            self.session_manager.close_session(session.session_id, "new_order_requested")
        
        new_session = await self.ws_handler.connect(websocket_id, websocket)
        
        await websocket.send_json({
            "type": "new_session",
            "session_id": new_session.session_id,
            "message": "New order started! What can I get for you?"
        })
    
    async def get_dashboard_data(self) -> Dict:
        """Get data for admin dashboard"""
        return self.session_manager.get_dashboard_data()
    
    async def get_global_stats(self) -> Dict:
        """Get global statistics"""
        return self.session_manager.get_global_stats()


# Singleton instance
_websocket_endpoint: Optional[ConcurrentWebSocketEndpoint] = None


async def get_websocket_endpoint() -> ConcurrentWebSocketEndpoint:
    """Get or create WebSocket endpoint singleton"""
    global _websocket_endpoint
    if _websocket_endpoint is None:
        _websocket_endpoint = ConcurrentWebSocketEndpoint()
        await _websocket_endpoint.startup()
    return _websocket_endpoint


async def shutdown_websocket():
    """Shutdown WebSocket endpoint"""
    global _websocket_endpoint
    if _websocket_endpoint:
        await _websocket_endpoint.shutdown()
        _websocket_endpoint = None
