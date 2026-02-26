"""
Order State Machine
Manages order lifecycle from creation to completion
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


class OrderState(Enum):
    """Order lifecycle states"""
    EMPTY = "empty"                    # No items yet
    BUILDING = "building"              # Adding items
    MODIFYING = "modifying"            # Changing existing order
    REVIEWING = "reviewing"            # Review before confirmation
    CONFIRMED = "confirmed"            # Order confirmed
    PREPARING = "preparing"            # Restaurant preparing
    READY = "ready"                    # Ready for pickup/delivery
    COMPLETED = "completed"            # Order delivered/picked up
    CANCELLED = "cancelled"            # Order cancelled


@dataclass
class OrderItem:
    """Individual order item"""
    id: str
    name: str
    category: str
    quantity: int
    unit_price: float
    
    # Modifiers
    flavor: Optional[str] = None
    wing_type: Optional[str] = None
    size: Optional[str] = None
    
    # Options
    dips: List[str] = field(default_factory=list)
    sides: List[str] = field(default_factory=list)
    drinks: List[str] = field(default_factory=list)
    
    # Pricing
    modifiers_price: float = 0.0
    
    @property
    def total_price(self) -> float:
        base = self.quantity * self.unit_price
        return base + self.modifiers_price
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "flavor": self.flavor,
            "wing_type": self.wing_type,
            "size": self.size,
            "dips": self.dips,
            "sides": self.sides,
            "drinks": self.drinks,
            "modifiers_price": self.modifiers_price,
            "total_price": self.total_price
        }


@dataclass
class Order:
    """Complete order with state management"""
    id: str
    session_id: str
    state: OrderState = OrderState.EMPTY
    
    # Customer info
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Order details
    items: List[OrderItem] = field(default_factory=list)
    order_type: str = "pickup"
    
    # Pricing
    subtotal: float = 0.0
    tax_rate: float = 0.08
    tax_amount: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    confirmed_at: Optional[datetime] = None
    
    # History
    state_history: List[dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.state_history:
            self._record_state_change(OrderState.EMPTY, "initialized")
    
    def _record_state_change(self, new_state: OrderState, reason: str):
        self.state_history.append({
            "from": self.state.value,
            "to": new_state.value,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        })
    
    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)
    
    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0
    
    def add_item(self, item: OrderItem):
        self.items.append(item)
        self._recalculate_totals()
        if self.state == OrderState.EMPTY:
            self.transition_to(OrderState.BUILDING, "first item added")
    
    def remove_item(self, item_id: str) -> bool:
        original_count = len(self.items)
        self.items = [item for item in self.items if item.id != item_id]
        removed = len(self.items) < original_count
        
        if removed:
            self._recalculate_totals()
            if self.is_empty:
                self.transition_to(OrderState.EMPTY, "all items removed")
        return removed
    
    def update_item(self, item_id: str, **kwargs) -> bool:
        for item in self.items:
            if item.id == item_id:
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                self._recalculate_totals()
                self.transition_to(OrderState.MODIFYING, f"item {item_id} modified")
                return True
        return False
    
    def _recalculate_totals(self):
        self.subtotal = sum(item.total_price for item in self.items)
        self.tax_amount = self.subtotal * self.tax_rate
        self.total = self.subtotal + self.tax_amount - self.discount
    
    def set_customer_info(self, name: str = None, phone: str = None):
        if name:
            self.customer_name = name
        if phone:
            self.customer_phone = phone
    
    def transition_to(self, new_state: OrderState, reason: str = "") -> bool:
        valid_transitions = ORDER_TRANSITIONS.get(self.state, set())
        
        if new_state not in valid_transitions and new_state != self.state:
            print(f"[Order] Invalid transition: {self.state.value} -> {new_state.value}")
            return False
        
        old_state = self.state
        self._record_state_change(new_state, reason)
        self.state = new_state
        
        if new_state == OrderState.CONFIRMED:
            self.confirmed_at = datetime.now()
        
        print(f"[Order] State: {old_state.value} -> {new_state.value} ({reason})")
        return True
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "state": self.state.value,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "items": [item.to_dict() for item in self.items],
            "order_type": self.order_type,
            "subtotal": round(self.subtotal, 2),
            "tax_amount": round(self.tax_amount, 2),
            "total": round(self.total, 2),
            "item_count": self.item_count
        }
    
    def get_summary(self) -> str:
        lines = [
            f"Order #{self.id[:8]} - {self.state.value.upper()}",
            f"Customer: {self.customer_name or 'Not provided'}",
            ""
        ]
        
        for item in self.items:
            lines.append(f"{item.quantity}x {item.name} - ${item.total_price:.2f}")
            if item.flavor:
                lines.append(f"  Flavor: {item.flavor}")
        
        lines.extend([
            "",
            f"Subtotal: ${self.subtotal:.2f}",
            f"Tax: ${self.tax_amount:.2f}",
            f"Total: ${self.total:.2f}"
        ])
        
        return "\n".join(lines)


# Valid state transitions
ORDER_TRANSITIONS = {
    OrderState.EMPTY: {OrderState.BUILDING, OrderState.CANCELLED},
    OrderState.BUILDING: {OrderState.MODIFYING, OrderState.REVIEWING, OrderState.EMPTY, OrderState.CANCELLED},
    OrderState.MODIFYING: {OrderState.BUILDING, OrderState.REVIEWING, OrderState.EMPTY, OrderState.CANCELLED},
    OrderState.REVIEWING: {OrderState.BUILDING, OrderState.MODIFYING, OrderState.CONFIRMED, OrderState.CANCELLED},
    OrderState.CONFIRMED: {OrderState.PREPARING, OrderState.CANCELLED},
    OrderState.PREPARING: {OrderState.READY, OrderState.CANCELLED},
    OrderState.READY: {OrderState.COMPLETED, OrderState.CANCELLED},
    OrderState.COMPLETED: set(),
    OrderState.CANCELLED: set()
}


class OrderManager:
    """Manages multiple orders across sessions"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
    
    def create_order(self, session_id: str, order_id: str = None) -> Order:
        import uuid
        if order_id is None:
            order_id = str(uuid.uuid4())
        
        order = Order(id=order_id, session_id=session_id)
        self.orders[session_id] = order
        print(f"[OrderManager] Created order {order_id[:8]}")
        return order
    
    def get_order(self, session_id: str) -> Optional[Order]:
        return self.orders.get(session_id)
    
    def get_or_create_order(self, session_id: str) -> Order:
        order = self.get_order(session_id)
        if order is None:
            order = self.create_order(session_id)
        return order
    
    def close_order(self, session_id: str) -> Optional[Order]:
        order = self.orders.pop(session_id, None)
        if order:
            print(f"[OrderManager] Closed order {order.id[:8]}")
        return order
