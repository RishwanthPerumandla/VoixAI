"""
Concurrent Session Manager
Handles multiple simultaneous customer sessions (one per browser tab)
"""

import uuid
import asyncio
from typing import Dict, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from src.orders.state_machine import OrderManager, Order, OrderState
from src.agent.cashier_agent import WingstopCashier


class SessionStatus(Enum):
    """Status of a customer session"""
    ACTIVE = "active"           # Currently ordering
    IDLE = "idle"               # Connected but no activity
    COMPLETED = "completed"     # Order finished
    DISCONNECTED = "disconnected"  # Tab closed
    EXPIRED = "expired"         # Session timeout


@dataclass
class ConcurrentSession:
    """A single customer session in concurrent environment"""
    session_id: str
    websocket_id: str          # WebSocket connection ID
    
    # Customer info
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Order reference
    order_id: Optional[str] = None
    
    # Session status
    status: SessionStatus = SessionStatus.ACTIVE
    
    # Metrics
    messages_count: int = 0
    
    def touch(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def mark_complete(self):
        """Mark session as completed"""
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def mark_disconnected(self):
        """Mark session as disconnected"""
        self.status = SessionStatus.DISCONNECTED
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active"""
        return self.status in [SessionStatus.ACTIVE, SessionStatus.IDLE]
    
    @property
    def duration_seconds(self) -> float:
        """Get session duration"""
        end = self.completed_at or datetime.now()
        return (end - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        """Get idle time"""
        return (datetime.now() - self.last_activity).total_seconds()


class ConcurrentSessionManager:
    """
    Manages multiple simultaneous customer sessions
    Each browser tab = one independent session
    """
    
    def __init__(self, session_timeout: int = 1800, cleanup_interval: int = 60):
        """
        Args:
            session_timeout: Seconds before idle session expires (default 30 min)
            cleanup_interval: Seconds between cleanup runs
        """
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        
        # Active sessions (session_id -> ConcurrentSession)
        self.sessions: Dict[str, ConcurrentSession] = {}
        
        # Order managers per session
        self.order_managers: Dict[str, OrderManager] = {}
        
        # WebSocket to session mapping
        self.websocket_sessions: Dict[str, str] = {}
        
        # Agents per session
        self.agents: Dict[str, WingstopCashier] = {}
        
        # Callbacks
        self.on_session_created: Optional[Callable] = None
        self.on_session_closed: Optional[Callable] = None
        self.on_order_completed: Optional[Callable] = None
        
        # Stats
        self.total_sessions_created: int = 0
        self.total_orders_completed: int = 0
        
        # Start cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
        print(f"[ConcurrentManager] Initialized - Supports multiple simultaneous sessions")
    
    async def start(self):
        """Start the manager and cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        print("[ConcurrentManager] Started cleanup loop")
    
    async def stop(self):
        """Stop the manager and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        print("[ConcurrentManager] Stopped")
    
    # ==================== Session Lifecycle ====================
    
    def create_session(self, websocket_id: str, 
                      customer_name: str = None) -> ConcurrentSession:
        """
        Create a new concurrent session
        Called when new WebSocket connection is established
        """
        # Generate unique session ID
        session_id = f"{uuid.uuid4().hex[:8]}"
        
        # Create session
        session = ConcurrentSession(
            session_id=session_id,
            websocket_id=websocket_id,
            customer_name=customer_name,
            status=SessionStatus.ACTIVE
        )
        
        # Create order manager for this session
        order_manager = OrderManager()
        order = order_manager.create_order(session_id)
        session.order_id = order.id
        
        # Create agent for this session
        agent = WingstopCashier()
        
        # Store everything
        self.sessions[session_id] = session
        self.order_managers[session_id] = order_manager
        self.websocket_sessions[websocket_id] = session_id
        self.agents[session_id] = agent
        
        self.total_sessions_created += 1
        
        print(f"[ConcurrentManager] New session: {session_id} (WebSocket: {websocket_id[:8]}...)")
        print(f"[ConcurrentManager] Active sessions: {len(self.get_active_sessions())}")
        
        if self.on_session_created:
            self.on_session_created(session)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ConcurrentSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def get_session_by_websocket(self, websocket_id: str) -> Optional[ConcurrentSession]:
        """Get session by WebSocket ID"""
        session_id = self.websocket_sessions.get(websocket_id)
        if session_id:
            return self.sessions.get(session_id)
        return None
    
    def close_session(self, session_id: str, reason: str = "closed"):
        """Close a session"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        session.mark_disconnected()
        
        # Clean up mappings
        if session.websocket_id in self.websocket_sessions:
            del self.websocket_sessions[session.websocket_id]
        
        print(f"[ConcurrentManager] Session closed: {session_id} ({reason})")
        print(f"[ConcurrentManager] Active sessions: {len(self.get_active_sessions())}")
        
        if self.on_session_closed:
            self.on_session_closed(session, reason)
    
    # ==================== Order Management ====================
    
    def get_order(self, session_id: str) -> Optional[Order]:
        """Get order for a session"""
        order_manager = self.order_managers.get(session_id)
        if order_manager:
            return order_manager.get_order(session_id)
        return None
    
    def complete_order(self, session_id: str) -> Optional[Order]:
        """Mark order as complete for a session"""
        session = self.sessions.get(session_id)
        order = self.get_order(session_id)
        
        if not session or not order:
            return None
        
        # Transition order state
        if order.state != OrderState.COMPLETED:
            order.transition_to(OrderState.COMPLETED, "order fulfilled")
        
        # Mark session complete
        session.mark_complete()
        self.total_orders_completed += 1
        
        print(f"[ConcurrentManager] Order completed: {order.id[:8]} for {session.customer_name}")
        
        if self.on_order_completed:
            self.on_order_completed(session, order)
        
        return order
    
    # ==================== Message Processing ====================
    
    async def process_message(self, session_id: str, message: str) -> str:
        """
        Process a message for a specific session
        Each session has its own isolated order context
        """
        session = self.sessions.get(session_id)
        if not session:
            return "Error: Session not found. Please refresh the page."
        
        # Update activity
        session.touch()
        session.messages_count += 1
        
        # Get agent for this session
        agent = self.agents.get(session_id)
        if not agent:
            return "Error: Agent not initialized."
        
        # Process through agent (isolated to this session)
        response = await agent.process(message, session_id)
        
        # Check if order just got confirmed/completed
        order = self.get_order(session_id)
        if order and order.state == OrderState.CONFIRMED and session.status == SessionStatus.ACTIVE:
            # Could auto-complete or wait for explicit confirmation
            pass
        
        return response
    
    # ==================== Session Queries ====================
    
    def get_active_sessions(self) -> List[ConcurrentSession]:
        """Get all active sessions"""
        return [s for s in self.sessions.values() if s.is_active]
    
    def get_active_orders(self) -> List[Order]:
        """Get all active (non-completed) orders"""
        orders = []
        for session in self.get_active_sessions():
            order = self.get_order(session.session_id)
            if order and order.state != OrderState.COMPLETED:
                orders.append(order)
        return orders
    
    def get_session_count(self) -> int:
        """Get total number of sessions"""
        return len(self.sessions)
    
    def get_active_count(self) -> int:
        """Get number of active sessions"""
        return len(self.get_active_sessions())
    
    def get_global_stats(self) -> Dict:
        """Get global statistics across all sessions"""
        active_orders = self.get_active_orders()
        completed_sessions = [s for s in self.sessions.values() 
                             if s.status == SessionStatus.COMPLETED]
        
        total_revenue = sum(
            self.get_order(s.session_id).total 
            for s in completed_sessions
            if self.get_order(s.session_id)
        )
        
        return {
            "total_sessions": self.total_sessions_created,
            "active_sessions": self.get_active_count(),
            "completed_orders": self.total_orders_completed,
            "active_orders": len(active_orders),
            "total_revenue": round(total_revenue, 2),
            "average_order_value": round(total_revenue / self.total_orders_completed, 2) 
                                  if self.total_orders_completed > 0 else 0,
            "sessions_by_status": {
                "active": len([s for s in self.sessions.values() if s.status == SessionStatus.ACTIVE]),
                "idle": len([s for s in self.sessions.values() if s.status == SessionStatus.IDLE]),
                "completed": len([s for s in self.sessions.values() if s.status == SessionStatus.COMPLETED]),
                "disconnected": len([s for s in self.sessions.values() if s.status == SessionStatus.DISCONNECTED]),
            }
        }
    
    def get_dashboard_data(self) -> Dict:
        """Get data for real-time dashboard"""
        active_sessions = self.get_active_sessions()
        
        session_data = []
        for session in active_sessions:
            order = self.get_order(session.session_id)
            session_data.append({
                "session_id": session.session_id,
                "customer": session.customer_name or "Anonymous",
                "status": session.status.value,
                "order_state": order.state.value if order else "none",
                "items": order.item_count if order else 0,
                "total": round(order.total, 2) if order else 0,
                "duration": int(session.duration_seconds),
                "messages": session.messages_count
            })
        
        return {
            "stats": self.get_global_stats(),
            "active_sessions": session_data,
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== Cleanup ====================
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired sessions"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ConcurrentManager] Cleanup error: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = []
        
        for session_id, session in self.sessions.items():
            # Check for idle timeout
            if session.status == SessionStatus.IDLE and session.idle_seconds > self.session_timeout:
                expired.append(session_id)
            # Check for disconnected timeout
            elif session.status == SessionStatus.DISCONNECTED and session.idle_seconds > 300:  # 5 min grace
                expired.append(session_id)
        
        for session_id in expired:
            self._remove_session(session_id)
            print(f"[ConcurrentManager] Cleaned up expired session: {session_id}")
    
    def _remove_session(self, session_id: str):
        """Remove a session and all its data"""
        session = self.sessions.get(session_id)
        if session:
            # Remove mappings
            if session.websocket_id in self.websocket_sessions:
                del self.websocket_sessions[session.websocket_id]
            
            # Remove session data
            self.sessions.pop(session_id, None)
            self.order_managers.pop(session_id, None)
            self.agents.pop(session_id, None)
    
    def force_cleanup_all(self):
        """Force cleanup of all sessions (use with caution)"""
        self.sessions.clear()
        self.order_managers.clear()
        self.websocket_sessions.clear()
        self.agents.clear()
        print("[ConcurrentManager] All sessions cleared")


# ==================== WebSocket Integration ====================

class WebSocketSessionHandler:
    """
    Handles WebSocket connections with session management
    One session per WebSocket connection (one per tab)
    """
    
    def __init__(self, session_manager: ConcurrentSessionManager):
        self.session_manager = session_manager
        self.connections: Dict[str, any] = {}  # websocket_id -> websocket object
    
    async def connect(self, websocket_id: str, websocket) -> ConcurrentSession:
        """Handle new WebSocket connection"""
        self.connections[websocket_id] = websocket
        
        # Create new session for this connection
        session = self.session_manager.create_session(websocket_id)
        
        return session
    
    async def disconnect(self, websocket_id: str):
        """Handle WebSocket disconnection"""
        session = self.session_manager.get_session_by_websocket(websocket_id)
        
        if session:
            # Mark as disconnected but keep session for potential reconnect
            session.mark_disconnected()
            self.session_manager.close_session(session.session_id, "websocket_disconnected")
        
        # Remove connection
        self.connections.pop(websocket_id, None)
    
    async def handle_message(self, websocket_id: str, message: str) -> str:
        """Handle message from a specific WebSocket"""
        session = self.session_manager.get_session_by_websocket(websocket_id)
        
        if not session:
            return "Error: Session not found. Please refresh the page."
        
        # Process through session manager
        response = await self.session_manager.process_message(
            session.session_id, 
            message
        )
        
        return response
    
    async def broadcast_to_all(self, message: Dict):
        """Broadcast message to all connected clients"""
        import json
        for ws_id, websocket in self.connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"[WebSocketHandler] Broadcast failed to {ws_id}: {e}")
