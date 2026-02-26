"""
Order Session Manager
Handles sequential customer orders - one at a time, reset after completion
"""

import uuid
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from src.orders.state_machine import OrderManager, Order, OrderState


class SessionState(Enum):
    """State of the ordering session"""
    IDLE = "idle"                      # Waiting for first customer
    GREETING = "greeting"              # Initial greeting
    TAKING_ORDER = "taking_order"      # Actively taking order
    CONFIRMING = "confirming"          # Confirming order details
    PROCESSING = "processing"          # Order sent to kitchen
    COMPLETED = "completed"            # Order done, ready for next
    TRANSITIONING = "transitioning"    # Between customers


@dataclass
class CustomerSession:
    """A single customer's ordering session"""
    session_id: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    order_completed_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Order reference
    order_id: Optional[str] = None
    
    # Session metrics
    messages_exchanged: int = 0
    total_duration_seconds: Optional[float] = None
    
    def mark_complete(self):
        """Mark session as completed"""
        self.order_completed_at = datetime.now()
    
    def end_session(self):
        """End the session"""
        self.ended_at = datetime.now()
        if self.started_at:
            self.total_duration_seconds = (self.ended_at - self.started_at).total_seconds()


class OrderSessionManager:
    """
    Manages sequential customer ordering sessions
    One customer at a time, auto-reset after completion
    """
    
    def __init__(self, auto_reset_delay: int = 5):
        """
        Args:
            auto_reset_delay: Seconds to wait before auto-reset after completion
        """
        self.order_manager = OrderManager()
        self.auto_reset_delay = auto_reset_delay
        
        # Current session tracking
        self.current_session: Optional[CustomerSession] = None
        self.session_state: SessionState = SessionState.IDLE
        self.active_session_id: Optional[str] = None
        
        # Session history
        self.completed_sessions: List[CustomerSession] = []
        self.max_history = 100
        
        # Callbacks
        self.on_session_start: Optional[Callable] = None
        self.on_session_end: Optional[Callable] = None
        self.on_order_complete: Optional[Callable] = None
        self.on_reset: Optional[Callable] = None
        
        print("[SessionManager] Initialized - Ready for customers")
    
    # ==================== Session Lifecycle ====================
    
    def start_new_session(self, customer_name: str = None, customer_phone: str = None) -> CustomerSession:
        """Start a new customer session"""
        # End current session if exists
        if self.current_session:
            self._end_current_session()
        
        # Create new session
        session_id = str(uuid.uuid4())[:8]
        self.current_session = CustomerSession(
            session_id=session_id,
            customer_name=customer_name,
            customer_phone=customer_phone
        )
        self.active_session_id = session_id
        self.session_state = SessionState.GREETING
        
        # Create order for this session
        order = self.order_manager.create_order(session_id)
        self.current_session.order_id = order.id
        
        print(f"[SessionManager] New session started: {session_id}")
        print(f"[SessionManager] Customer: {customer_name or 'Unknown'}")
        
        if self.on_session_start:
            self.on_session_start(self.current_session)
        
        return self.current_session
    
    def get_or_create_session(self, session_id: str = None, 
                             customer_name: str = None) -> CustomerSession:
        """Get existing session or create new one"""
        # If no current session, start new
        if not self.current_session:
            return self.start_new_session(customer_name)
        
        # If session completed, start new
        if self.session_state in [SessionState.COMPLETED, SessionState.IDLE]:
            return self.start_new_session(customer_name)
        
        # Update customer info if provided
        if customer_name and not self.current_session.customer_name:
            self.current_session.customer_name = customer_name
        
        return self.current_session
    
    def _end_current_session(self):
        """End the current session and archive it"""
        if not self.current_session:
            return
        
        self.current_session.end_session()
        self.completed_sessions.append(self.current_session)
        
        # Trim history
        if len(self.completed_sessions) > self.max_history:
            self.completed_sessions = self.completed_sessions[-self.max_history:]
        
        print(f"[SessionManager] Session ended: {self.current_session.session_id}")
        
        if self.on_session_end:
            self.on_session_end(self.current_session)
        
        self.current_session = None
        self.active_session_id = None
    
    def complete_order(self, order: Order) -> CustomerSession:
        """Mark current order as complete and prepare for next customer"""
        if not self.current_session:
            raise ValueError("No active session")
        
        # Mark order complete
        order.transition_to(OrderState.COMPLETED, "order fulfilled")
        self.current_session.mark_complete()
        self.session_state = SessionState.COMPLETED
        
        print(f"[SessionManager] Order completed for {self.current_session.customer_name}")
        print(f"[SessionManager] Session duration: {self.current_session.total_duration_seconds}s")
        
        if self.on_order_complete:
            self.on_order_complete(self.current_session, order)
        
        return self.current_session
    
    def reset_for_next_customer(self) -> CustomerSession:
        """Explicitly reset for next customer"""
        print("[SessionManager] Resetting for next customer...")
        
        # End current session
        self._end_current_session()
        
        # Clear order manager
        self.order_manager = OrderManager()
        
        # Reset state
        self.session_state = SessionState.IDLE
        
        if self.on_reset:
            self.on_reset()
        
        print("[SessionManager] Ready for next customer!")
        
        # Start new session automatically
        return self.start_new_session()
    
    # ==================== State Management ====================
    
    def update_state(self, new_state: SessionState):
        """Update session state"""
        old_state = self.session_state
        self.session_state = new_state
        print(f"[SessionManager] State: {old_state.value} -> {new_state.value}")
    
    def is_ready_for_new_customer(self) -> bool:
        """Check if ready to take a new order"""
        if not self.current_session:
            return True
        return self.session_state in [SessionState.IDLE, SessionState.COMPLETED]
    
    def get_current_order(self) -> Optional[Order]:
        """Get the current active order"""
        if not self.current_session:
            return None
        return self.order_manager.get_order(self.current_session.session_id)
    
    # ==================== Session Info ====================
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        if not self.current_session:
            return {"status": "no_session"}
        
        order = self.get_current_order()
        
        return {
            "status": "active",
            "session_id": self.current_session.session_id,
            "customer": self.current_session.customer_name or "Unknown",
            "session_state": self.session_state.value,
            "order_state": order.state.value if order else "none",
            "items": order.item_count if order else 0,
            "total": order.total if order else 0.0,
            "duration_seconds": self._get_session_duration()
        }
    
    def _get_session_duration(self) -> float:
        """Get current session duration"""
        if not self.current_session:
            return 0.0
        return (datetime.now() - self.current_session.started_at).total_seconds()
    
    def get_daily_stats(self) -> Dict:
        """Get statistics for today's sessions"""
        today = datetime.now().date()
        
        today_sessions = [
            s for s in self.completed_sessions 
            if s.started_at.date() == today
        ]
        
        if self.current_session and self.current_session.started_at.date() == today:
            today_sessions.append(self.current_session)
        
        total_revenue = sum(
            self.order_manager.get_order(s.session_id).total 
            for s in today_sessions 
            if s.order_id and self.order_manager.get_order(s.session_id)
        )
        
        return {
            "total_sessions": len(today_sessions),
            "completed_orders": len([s for s in today_sessions if s.order_completed_at]),
            "total_revenue": total_revenue,
            "avg_session_duration": sum(
                s.total_duration_seconds or 0 for s in today_sessions
            ) / len(today_sessions) if today_sessions else 0
        }
    
    # ==================== Customer Queue (Optional) ====================
    
    def get_next_customer_greeting(self) -> str:
        """Get greeting for next customer based on state"""
        if self.session_state == SessionState.IDLE:
            return "Welcome to Wingstop! What can I get for you today?"
        elif self.session_state == SessionState.COMPLETED:
            return "Thanks! Next customer please. Hi there! What would you like to order?"
        else:
            return "Hi! What can I get you?"


class MultiCustomerAgent:
    """
    Agent that handles multiple customers sequentially
    Wraps OrderCentricAgent with session management
    """
    
    def __init__(self, order_agent):
        self.order_agent = order_agent
        self.session_manager = OrderSessionManager()
        
        # Set up callbacks
        self.session_manager.on_order_complete = self._on_order_complete
        self.session_manager.on_reset = self._on_reset
    
    async def process(self, user_message: str, session_id: str = None) -> str:
        """Process message with session management"""
        
        # Check if we need to start new session
        if self.session_manager.is_ready_for_new_customer():
            # Extract customer name if provided
            customer_name = self._extract_customer_name(user_message)
            self.session_manager.start_new_session(customer_name)
        
        # Get current session
        session = self.session_manager.current_session
        
        # Update session metrics
        session.messages_exchanged += 1
        
        # Check for completion signals
        if self._is_order_complete_signal(user_message):
            order = self.session_manager.get_current_order()
            if order and order.state == OrderState.CONFIRMED:
                self.session_manager.complete_order(order)
                return self._get_completion_message(session)
        
        # Check for new customer signal
        if self._is_new_customer_signal(user_message):
            self.session_manager.reset_for_next_customer()
            return self.session_manager.get_next_customer_greeting()
        
        # Process through order agent
        response = await self.order_agent.process(user_message, session.session_id)
        
        # Update session state based on order state
        order = self.session_manager.get_current_order()
        if order:
            self._sync_session_state(order.state)
        
        return response
    
    def _extract_customer_name(self, message: str) -> Optional[str]:
        """Extract customer name from message"""
        import re
        patterns = [
            r'name is (\w+)',
            r'for (\w+)$',
            r'^it\'?s (\w+)',
            r'^(\w+) here',
        ]
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1).title()
        return None
    
    def _is_order_complete_signal(self, message: str) -> bool:
        """Check if message signals order completion"""
        completion_phrases = [
            "order complete", "done with this order", "that\'s all",
            "order finished", "customer served"
        ]
        return any(phrase in message.lower() for phrase in completion_phrases)
    
    def _is_new_customer_signal(self, message: str) -> bool:
        """Check if message signals new customer"""
        new_customer_phrases = [
            "next customer", "new customer", "next please",
            "ready for next", "help the next person"
        ]
        return any(phrase in message.lower() for phrase in new_customer_phrases)
    
    def _sync_session_state(self, order_state: OrderState):
        """Sync session state with order state"""
        state_map = {
            OrderState.EMPTY: SessionState.TAKING_ORDER,
            OrderState.BUILDING: SessionState.TAKING_ORDER,
            OrderState.MODIFYING: SessionState.TAKING_ORDER,
            OrderState.REVIEWING: SessionState.CONFIRMING,
            OrderState.CONFIRMED: SessionState.PROCESSING,
            OrderState.COMPLETED: SessionState.COMPLETED,
        }
        new_state = state_map.get(order_state, SessionState.TAKING_ORDER)
        self.session_manager.update_state(new_state)
    
    def _get_completion_message(self, session: CustomerSession) -> str:
        """Generate completion message"""
        return (
            f"Order complete for {session.customer_name or 'customer'}! "
            f"Say 'next customer' when ready for the next person."
        )
    
    def _on_order_complete(self, session: CustomerSession, order: Order):
        """Callback when order is completed"""
        print(f"[MultiCustomerAgent] Order completed: {order.id[:8]} for {session.customer_name}")
    
    def _on_reset(self):
        """Callback when system resets"""
        print("[MultiCustomerAgent] System reset for next customer")
    
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "session": self.session_manager.get_session_summary(),
            "daily_stats": self.session_manager.get_daily_stats(),
            "ready_for_new": self.session_manager.is_ready_for_new_customer()
        }
