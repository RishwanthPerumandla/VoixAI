# VoixAI Order-Based System

**Status:** IMPLEMENTED  
**Date:** 2025-02-25

---

## Overview

The system is now order-centric, with all interactions flowing through the order management lifecycle. The order is the central entity that drives the conversation.

---

## Order Lifecycle

```
EMPTY -> BUILDING -> MODIFYING -> REVIEWING -> CONFIRMED -> PREPARING -> READY -> COMPLETED
              |         |            |            |
              v         v            v            v
          CANCELLED (can happen from any non-terminal state)
```

### States

| State | Description | Actions |
|-------|-------------|---------|
| `EMPTY` | No items in order | Add items |
| `BUILDING` | Adding items | Add, remove, modify |
| `MODIFYING` | Changing existing items | Update, remove |
| `REVIEWING` | Customer reviewing order | Modify, confirm, cancel |
| `CONFIRMED` | Order placed | Track status |
| `PREPARING` | Restaurant preparing | Wait |
| `READY` | Ready for pickup | Pick up |
| `COMPLETED` | Order finished | Done |
| `CANCELLED` | Order cancelled | Start over |

---

## Core Components

### 1. Order State Machine (`src/orders/state_machine.py`)

**Classes:**
- `Order` - Complete order with state management
- `OrderItem` - Individual order line item
- `OrderManager` - Manages orders across sessions
- `OrderState` - Enum of order states

**Features:**
- State transitions with history tracking
- Automatic total calculation (subtotal, tax, total)
- Customer info management
- Item modifiers (flavor, size, dips, sides)

**Example:**
```python
from src.orders.state_machine import OrderManager, OrderItem

manager = OrderManager()
order = manager.create_order("session-123")

item = OrderItem(
    id="item_0",
    name="Boneless Wings",
    category="wings",
    quantity=10,
    unit_price=1.29,
    flavor="Lemon Pepper"
)
order.add_item(item)
order.set_customer_info(name="John", phone="555-1234")
order.transition_to(OrderState.CONFIRMED)
```

---

### 2. Order-Centric Agent (`src/orders/order_agent.py`)

**Classes:**
- `OrderCentricAgent` - ReAct agent focused on order workflows
- `OrderUnderstandingEngine` - Parses order intents
- `OrderReasoningEngine` - Decides order actions
- `OrderResponseGenerator` - Generates order-focused responses

**Intents Recognized:**
- `add_item` - Add items to order
- `remove_item` - Remove items
- `modify_item` - Change existing items
- `review` - Show order summary
- `confirm` - Place order
- `cancel` - Cancel order
- `query` - General questions

**Example:**
```python
from src.orders.order_agent import OrderCentricAgent

agent = OrderCentricAgent()
response = await agent.process("I want 10 boneless wings", "session-123")
```

---

### 3. Order Validation (`src/orders/validation.py`)

**Classes:**
- `OrderValidator` - Runs all validation rules
- `OrderRequirementsChecker` - Progressive requirement checking
- Individual rule classes

**Validation Rules:**
- `MinimumOrderValueRule` - Min $5.00
- `MaximumOrderValueRule` - Max $200.00
- `RequiredCustomerInfoRule` - Name required
- `FlavorRequiredRule` - Wings need flavor
- `ComboValidationRule` - Suggest combos
- `MaximumItemsRule` - Max 20 items
- `DuplicateItemRule` - Detect duplicates

**Example:**
```python
from src.orders.validation import OrderValidator

validator = OrderValidator()
result = validator.validate(order)

if result['can_submit']:
    print("Order is valid!")
else:
    print(f"Errors: {result['errors']}")
    print(f"Suggestions: {result['suggestions']}")
```

---

## Order Structure

```python
Order {
    id: str                    # Unique order ID
    session_id: str            # Customer session
    state: OrderState          # Current state
    
    customer_name: str         # Customer info
    customer_phone: str
    
    items: [OrderItem]         # Line items
    order_type: str            # pickup/delivery/dine-in
    
    subtotal: float            # Pricing
    tax_amount: float
    total: float
    
    created_at: datetime       # Timestamps
    confirmed_at: datetime
    
    state_history: [dict]      # Transition history
}

OrderItem {
    id: str
    name: str
    category: str             # wings, sides, drinks, etc.
    quantity: int
    unit_price: float
    
    flavor: str               # Lemon Pepper, etc.
    wing_type: str            # boneless, bone-in
    size: str                 # 8pc, 10pc, etc.
    
    dips: [str]               # Options
    sides: [str]
    drinks: [str]
    
    total_price: float        # Computed
}
```

---

## Integration with Existing Tools

The order system integrates with the existing 8 tools:

| Tool | Usage |
|------|-------|
| `search_menu` | Find items to add |
| `calculate_price` | Compute totals |
| `create_order` | Persist confirmed orders |
| `modify_order` | Update existing orders |
| `validate_order` | Check order completeness |
| `suggest_upsell` | Recommend add-ons |
| `check_policy` | Validate against rules |
| `create_ticket` | Handle issues |

---

## Conversation Flow Examples

### Flow 1: Simple Order
```
Customer: "I want 10 boneless wings"
Agent: "Added Boneless Wings. Which flavor?"

Customer: "Lemon pepper"
Agent: "Got it! Added Lemon Pepper flavor. What else?"

Customer: "That's it"
Agent: "What's the name for the order?"

Customer: "John"
Agent: "So far you have:\n10x Boneless Wings (Lemon Pepper)\nTotal: $12.85\n\nReady to confirm?"

Customer: "Yes"
Agent: "Order #abc123 confirmed! Total: $12.85"
```

### Flow 2: Modify Order
```
Customer: "Actually make it 15 wings"
Agent: "Updated to 15 wings. New total: $18.52"
```

### Flow 3: Review
```
Customer: "What's in my order?"
Agent: "Order #abc123:\n10x Boneless Wings (Lemon Pepper)\nTotal: $12.85"
```

---

## Testing

```bash
# Run order workflow tests
python scripts/test_order_workflows.py
```

**Test Coverage:**
- State machine transitions
- Order validation rules
- Agent intent parsing
- Order persistence

---

## Files Added

```
src/orders/
├── __init__.py
├── state_machine.py      # Order lifecycle management
├── order_agent.py        # Order-centric agent
└── validation.py         # Order validation rules

scripts/
└── test_order_workflows.py  # Order system tests

docs/
└── ORDER_SYSTEM.md       # This document
```

---

## Next Steps

1. **Integration** - Connect OrderCentricAgent to main pipeline
2. **Persistence** - Save orders to database on confirm
3. **WebSocket** - Stream order updates to client
4. **POS Integration** - Send confirmed orders to restaurant
