# VoixAI Concurrent Sessions

**Multiple Simultaneous Customer Support**

Each browser tab = One independent customer session

---

## Overview

The system now supports **concurrent customers** ordering simultaneously. Each browser tab creates a completely isolated session with its own order, agent, and state.

```
Tab 1 (Rishi)          Tab 2 (Sarah)          Tab 3 (Mike)
    |                       |                       |
    v                       v                       v
Session #1             Session #2             Session #3
Order #A               Order #B               Order #C
    |                       |                       |
    v                       v                       v
10 Boneless Wings     15 Bone-In Wings      Combo Meal
Lemon Pepper          Garlic Parmesan       + Drink + Fries
$12.85                $20.90                $26.99
```

All three customers can order at the same time without interfering with each other.

---

## Architecture

### Session Management

```
┌─────────────────────────────────────────────────────────────┐
│                  ConcurrentSessionManager                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  sessions: {                                                 │
│    "abc123": ConcurrentSession (Rishi),                     │
│    "def456": ConcurrentSession (Sarah),                     │
│    "ghi789": ConcurrentSession (Mike)                       │
│  }                                                           │
│                                                              │
│  order_managers: {                                           │
│    "abc123": OrderManager (Rishi's order),                  │
│    "def456": OrderManager (Sarah's order),                  │
│    "ghi789": OrderManager (Mike's order)                    │
│  }                                                           │
│                                                              │
│  agents: {                                                   │
│    "abc123": OrderCentricAgent (Rishi's agent),             │
│    "def456": OrderCentricAgent (Sarah's agent),             │
│    "ghi789": OrderCentricAgent (Mike's agent)               │
│  }                                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### WebSocket Handling

```
WebSocket 1 (ws_abc) ──┐
                       ├──► Session "s1" ──► Order "o1"
WebSocket 2 (ws_def) ──┤
                       ├──► Session "s2" ──► Order "o2"
WebSocket 3 (ws_ghi) ──┘
                       └──► Session "s3" ──► Order "o3"
```

---

## Key Features

### 1. True Isolation

Each session has:
- Unique session ID
- Independent order state
- Separate agent instance
- Isolated conversation history

### 2. Per-Tab Sessions

- Open 3 tabs = 3 separate customers
- Close tab = Session marked disconnected (grace period)
- Refresh tab = New session created

### 3. Global Dashboard

Real-time view of all active orders:
```json
{
  "stats": {
    "total_sessions": 15,
    "active_sessions": 3,
    "active_orders": 3,
    "total_revenue": 485.50
  },
  "active_sessions": [
    {"customer": "Rishi", "order_state": "building", "total": 12.85},
    {"customer": "Sarah", "order_state": "reviewing", "total": 20.90},
    {"customer": "Mike", "order_state": "building", "total": 26.99}
  ]
}
```

### 4. Automatic Cleanup

- Idle sessions timeout after 30 minutes
- Disconnected sessions cleaned up after 5 minutes
- Background cleanup task runs every minute

---

## Usage

### Basic Setup

```python
from src.orders.concurrent_manager import ConcurrentSessionManager

# Initialize
manager = ConcurrentSessionManager(
    session_timeout=1800,  # 30 minutes
    cleanup_interval=60     # Cleanup every minute
)

await manager.start()
```

### Create Session (New Tab)

```python
# When WebSocket connects
session = manager.create_session(
    websocket_id="ws_abc123",
    customer_name="Rishi"
)

print(f"Session created: {session.session_id}")
# Each tab gets unique session
```

### Process Message

```python
# Process customer message (isolated to their session)
response = await manager.process_message(
    session_id="abc123",
    message="I want 10 boneless wings"
)

# Response is specific to this customer's order context
```

### Get Order

```python
# Get customer's order
order = manager.get_order(session_id)

print(f"Items: {order.item_count}")
print(f"Total: ${order.total}")
```

### Complete Order

```python
# Mark order as complete
manager.complete_order(session_id)

# Customer can start new order or close tab
```

### Close Session (Tab Closed)

```python
# When WebSocket disconnects
manager.close_session(session_id, reason="tab_closed")
```

---

## WebSocket Integration

```python
from fastapi import WebSocket
from src.api.websocket_concurrent import get_websocket_endpoint

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ws_endpoint = await get_websocket_endpoint()
    await ws_endpoint.handle_connection(websocket)
```

### Message Flow

```
Customer (Tab 1)          Server
    |                        |
    |── "10 boneless wings" ─►│
    |                        ├──► Session #1
    |                        │      └── Agent #1
    |◄── "Added! Flavor?" ───│
    |                        |
    
Customer (Tab 2)          Server
    |                        |
    |── "15 bone-in wings" ──►│
    |                        ├──► Session #2  (isolated)
    |                        │      └── Agent #2
    |◄── "Added! Flavor?" ───│
```

---

## Testing

```bash
# Run concurrent session tests
python scripts/test_concurrent_sessions.py
```

### Test Scenarios

1. **Multiple Simultaneous Sessions** - 3+ customers at once
2. **Session Isolation** - Orders don't interfere
3. **Message Processing** - Independent responses
4. **Cleanup** - Expired sessions removed

---

## Files

```
src/orders/
├── concurrent_manager.py    # ConcurrentSessionManager
├── session_manager.py       # Sequential manager (legacy)
├── state_machine.py         # Order + OrderItem
├── order_agent.py           # OrderCentricAgent
└── validation.py            # Order validation

src/api/
└── websocket_concurrent.py  # WebSocket endpoint

scripts/
└── test_concurrent_sessions.py  # Test suite

docs/
├── CONCURRENT_SESSIONS.md   # This file
└── MULTI_CUSTOMER_GUIDE.md  # Sequential guide
```

---

## Configuration

```python
# Session timeout (seconds)
manager = ConcurrentSessionManager(session_timeout=1800)

# Cleanup interval (seconds)
manager = ConcurrentSessionManager(cleanup_interval=60)

# Callbacks
manager.on_session_created = lambda s: print(f"New: {s.customer_name}")
manager.on_session_closed = lambda s, r: print(f"Closed: {s.customer_name}")
manager.on_order_completed = lambda s, o: print(f"Done: {o.id}")
```

---

## Comparison: Sequential vs Concurrent

| Feature | Sequential | Concurrent |
|---------|-----------|------------|
| Customers at once | 1 | Unlimited |
| Session isolation | N/A | Full isolation |
| Per-tab orders | No | Yes |
| Dashboard | Simple | Real-time multi-session |
| Use case | Phone/kiosk | Web ordering |
| Complexity | Low | Medium |

---

## Example: 3 Customers Simultaneously

```python
# Customer 1 opens tab
session1 = manager.create_session("ws_1", "Rishi")
await manager.process_message(session1.session_id, "10 boneless wings")

# Customer 2 opens tab (same time)
session2 = manager.create_session("ws_2", "Sarah")
await manager.process_message(session2.session_id, "15 bone-in wings")

# Customer 3 opens tab (same time)
session3 = manager.create_session("ws_3", "Mike")
await manager.process_message(session3.session_id, "Combo meal")

# All three orders are independent
order1 = manager.get_order(session1.session_id)  # Rishi's order
order2 = manager.get_order(session2.session_id)  # Sarah's order
order3 = manager.get_order(session3.session_id)  # Mike's order

# Global stats
stats = manager.get_global_stats()
print(f"Active: {stats['active_sessions']}")  # 3
print(f"Revenue: ${stats['total_revenue']}")   # $60.74
```

---

## Summary

| Feature | Status |
|---------|--------|
| Multi-tab support | ✅ |
| Session isolation | ✅ |
| Concurrent processing | ✅ |
| Global dashboard | ✅ |
| Auto-cleanup | ✅ |
| Per-session agents | ✅ |

The system now supports unlimited simultaneous customers, each with their own isolated ordering experience!
