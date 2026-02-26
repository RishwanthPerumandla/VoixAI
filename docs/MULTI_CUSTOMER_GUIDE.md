# VoixAI Multi-Customer Guide

**Sequential Customer Ordering System**

Handle one customer at a time, auto-reset after completion.

---

## Quick Start

```python
from src.orders.session_manager import OrderSessionManager
from src.orders.order_agent import OrderCentricAgent
from src.orders.state_machine import OrderItem

# Initialize
manager = OrderSessionManager()

# Customer 1 arrives
session1 = manager.start_new_session(customer_name="Rishi")
order = manager.get_current_order()

# Add items
item = OrderItem(
    id="item_0", name="Boneless Wings", category="wings",
    quantity=10, unit_price=1.29, flavor="Lemon Pepper"
)
order.add_item(item)
order.set_customer_info(name="Rishi")

# Confirm order
order.transition_to(OrderState.CONFIRMED)
manager.complete_order(order)

# Reset for next customer
manager.reset_for_next_customer()

# Customer 2 arrives (fresh session)
session2 = manager.start_new_session(customer_name="Sarah")
# ... take order ...
```

---

## How It Works

### Session Lifecycle

```
IDLE -> GREETING -> TAKING_ORDER -> CONFIRMING -> PROCESSING -> COMPLETED -> TRANSITIONING -> IDLE
                                                                     |
                                                                     v
                                                             (Next Customer)
```

### Key Behaviors

1. **One at a time** - Only one active customer session
2. **Auto-track** - Each customer gets unique session ID
3. **Archive** - Completed sessions saved to history
4. **Reset** - Clean slate for each new customer
5. **Stats** - Track daily orders, revenue, session times

---

## Usage Patterns

### Pattern 1: Manual Reset

```python
# Complete order for Rishi
manager.complete_order(order)

# Explicitly reset
manager.reset_for_next_customer()

# Start Sarah's order
session = manager.start_new_session(customer_name="Sarah")
```

### Pattern 2: Auto-Reset on New Session

```python
# Rishi's order completed
manager.complete_order(order)

# When next customer arrives, auto-starts fresh
session = manager.get_or_create_session(customer_name="Next Customer")
# Previous order automatically archived
```

### Pattern 3: Voice Commands

```python
# Use MultiCustomerAgent for voice-triggered handoffs
agent = MultiCustomerAgent(order_agent)

# Customer says they're done
response = await agent.process("That's all for me")
# -> "Order complete! Next customer please."

# Next customer arrives
response = await agent.process("Hi, I'm the next customer")
# -> "Hi! What would you like to order?"
```

---

## Session Management

### Start Session

```python
session = manager.start_new_session(
    customer_name="Rishi",
    customer_phone="555-1234"
)
print(f"Session ID: {session.session_id}")
```

### Get Current Status

```python
status = manager.get_session_summary()
print(status)
# {
#   "status": "active",
#   "session_id": "abc123",
#   "customer": "Rishi",
#   "session_state": "taking_order",
#   "order_state": "building",
#   "items": 10,
#   "total": 12.85,
#   "duration_seconds": 45.2
# }
```

### Check if Ready for New Customer

```python
if manager.is_ready_for_new_customer():
    # Previous order completed, safe to take next
    session = manager.start_new_session()
```

### Complete and Archive

```python
# Mark order complete
manager.complete_order(order)

# Access completed sessions
for session in manager.completed_sessions:
    print(f"{session.customer_name}: ${session.order_total}")
```

---

## Daily Statistics

```python
stats = manager.get_daily_stats()
print(stats)
# {
#   "total_sessions": 25,
#   "completed_orders": 23,
#   "total_revenue": 485.50,
#   "avg_session_duration": 180.5
# }
```

---

## Integration with WebSocket

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize session manager for this connection
    session_manager = OrderSessionManager()
    
    while True:
        message = await websocket.receive_text()
        
        # Process through multi-customer agent
        response = await agent.process(message)
        
        # Check if order just completed
        if session_manager.session_state == SessionState.COMPLETED:
            await websocket.send_json({
                "type": "order_complete",
                "message": response,
                "next_action": "Say 'next customer' to continue"
            })
        else:
            await websocket.send_json({
                "type": "response",
                "message": response
            })
```

---

## Configuration

```python
# Auto-reset delay (seconds after completion)
manager = OrderSessionManager(auto_reset_delay=10)

# Maximum history to keep
manager.max_history = 50

# Callbacks
manager.on_session_start = lambda s: print(f"Started: {s.customer_name}")
manager.on_session_end = lambda s: print(f"Ended: {s.customer_name}")
manager.on_order_complete = lambda s, o: print(f"Completed: {o.id}")
manager.on_reset = lambda: print("Ready for next!")
```

---

## Example Conversations

### Customer 1: Rishi

```
Customer: Hi, I'd like to order
Agent: Welcome! What can I get for you?

Customer: 10 boneless wings, lemon pepper
Agent: Got it! Added 10 boneless wings with lemon pepper. What else?

Customer: That's all, name is Rishi
Agent: Thanks Rishi! Your total is $12.85. Confirm?

Customer: Yes
Agent: Order #abc123 confirmed! Next customer please.
```

### Customer 2: Sarah (Auto-reset)

```
Customer: Hi, I'm Sarah
Agent: Hi Sarah! What would you like to order?

Customer: 15 bone-in wings with garlic parmesan
Agent: Added 15 bone-in wings with garlic parmesan. What else?

Customer: That's it
Agent: Thanks Sarah! Your total is $20.90. Confirm?

Customer: Yes place it
Agent: Order #def456 confirmed! Next customer please.
```

---

## Testing

```bash
# Run multi-customer tests
python scripts/test_multi_customer.py
```

**Tests:**
- Session lifecycle (start → complete → reset)
- Multi-customer agent workflows
- Auto-reset functionality
- Daily stats tracking

---

## Files

```
src/orders/
├── session_manager.py      # OrderSessionManager + MultiCustomerAgent
└── state_machine.py        # Order + OrderManager

scripts/
└── test_multi_customer.py  # Test suite

docs/
└── MULTI_CUSTOMER_GUIDE.md # This file
```

---

## Summary

| Feature | Description |
|---------|-------------|
| Sequential handling | One customer at a time |
| Auto-reset | Clean slate for each customer |
| Session tracking | Unique ID per customer |
| History archive | Keep completed sessions |
| Daily stats | Revenue, orders, duration |
| Voice triggers | "Next customer" to reset |
