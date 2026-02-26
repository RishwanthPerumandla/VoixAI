#!/usr/bin/env python3
"""
Test Order-Based Workflows
Tests the order-centric agent and state management
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orders.state_machine import OrderManager, OrderItem, OrderState
from src.orders.order_agent import OrderCentricAgent
from src.orders.validation import OrderValidator


async def test_order_state_machine():
    """Test order state transitions"""
    print("\n=== Testing Order State Machine ===")
    
    manager = OrderManager()
    session_id = "test-session-001"
    
    # Create order
    order = manager.create_order(session_id)
    assert order.state == OrderState.EMPTY
    print(f"Created order: {order.id[:8]}")
    
    # Add item
    item = OrderItem(
        id="item_0",
        name="Boneless Wings",
        category="wings",
        quantity=10,
        unit_price=1.29,
        flavor="Lemon Pepper"
    )
    order.add_item(item)
    assert order.state == OrderState.BUILDING
    print(f"Added item: {item.name} ({item.flavor})")
    print(f"Order total: ${order.total:.2f}")
    
    # Set customer info
    order.set_customer_info(name="Test Customer", phone="555-1234")
    print(f"Customer: {order.customer_name}")
    
    # Transition to review
    order.transition_to(OrderState.REVIEWING, "customer requested review")
    assert order.state == OrderState.REVIEWING
    print(f"State: {order.state.value}")
    
    # Confirm order
    order.transition_to(OrderState.CONFIRMED, "customer confirmed")
    assert order.state == OrderState.CONFIRMED
    assert order.confirmed_at is not None
    print(f"Order confirmed at: {order.confirmed_at}")
    
    print("State machine test: PASSED")
    return True


async def test_order_validation():
    """Test order validation rules"""
    print("\n=== Testing Order Validation ===")
    
    manager = OrderManager()
    validator = OrderValidator()
    
    # Test empty order
    order = manager.create_order("test-session-002")
    result = validator.validate(order)
    assert not result['can_submit']
    assert len(result['errors']) > 0
    print(f"Empty order validation: {len(result['errors'])} errors (expected)")
    
    # Add item but no flavor
    item = OrderItem(
        id="item_0",
        name="Boneless Wings",
        category="wings",
        quantity=10,
        unit_price=1.29
    )
    order.add_item(item)
    result = validator.validate(order)
    assert not result['can_submit']
    print(f"Missing flavor validation: {len(result['errors'])} errors (expected)")
    
    # Add flavor but no customer name
    item.flavor = "Lemon Pepper"
    result = validator.validate(order)
    assert not result['can_submit']
    assert any('name' in e.get('field', '') for e in result['errors'])
    print(f"Missing customer validation: {len(result['errors'])} errors (expected)")
    
    # Complete order
    order.set_customer_info(name="Test Customer")
    result = validator.validate(order)
    assert result['can_submit']
    print(f"Complete order validation: PASSED (can submit)")
    
    # Check combo suggestion
    assert len(result['suggestions']) > 0
    print(f"Combo suggestion: {result['suggestions'][0]['message']}")
    
    print("Validation test: PASSED")
    return True


async def test_order_agent():
    """Test order-centric agent"""
    print("\n=== Testing Order-Centric Agent ===")
    
    agent = OrderCentricAgent()
    session_id = "test-session-003"
    
    # Test 1: Empty order greeting
    response = await agent.process("Hi, I'd like to order", session_id)
    print(f"User: 'Hi, I'd like to order'")
    print(f"Agent: {response}")
    
    # Test 2: Add wings
    response = await agent.process("I want 10 boneless wings", session_id)
    print(f"\nUser: 'I want 10 boneless wings'")
    print(f"Agent: {response}")
    
    # Check order state
    status = agent.get_order_status(session_id)
    print(f"Order status: {status}")
    
    # Test 3: Add flavor
    response = await agent.process("Make it lemon pepper", session_id)
    print(f"\nUser: 'Make it lemon pepper'")
    print(f"Agent: {response}")
    
    # Test 4: Review order
    response = await agent.process("What's in my order?", session_id)
    print(f"\nUser: 'What's in my order?'")
    print(f"Agent: {response[:200]}...")
    
    # Test 5: Provide name
    response = await agent.process("Name is John", session_id)
    print(f"\nUser: 'Name is John'")
    print(f"Agent: {response}")
    
    print("\nAgent test: PASSED")
    return True


async def test_order_persistence():
    """Test order persistence to database"""
    print("\n=== Testing Order Persistence ===")
    
    # This would test the full database integration
    # For now, just verify the order dict serialization
    manager = OrderManager()
    order = manager.create_order("test-session-004")
    
    item = OrderItem(
        id="item_0",
        name="Boneless Wings",
        category="wings",
        quantity=10,
        unit_price=1.29,
        flavor="Lemon Pepper"
    )
    order.add_item(item)
    order.set_customer_info(name="Test Customer")
    
    # Serialize
    order_dict = order.to_dict()
    assert 'id' in order_dict
    assert 'items' in order_dict
    assert len(order_dict['items']) == 1
    print(f"Order serialization: PASSED")
    
    # Check summary
    summary = order.get_summary()
    assert 'Boneless Wings' in summary
    assert 'Lemon Pepper' in summary
    print(f"Order summary generation: PASSED")
    
    print("Persistence test: PASSED")
    return True


async def main():
    """Run all order workflow tests"""
    print("=" * 60)
    print("Order-Based Workflow Tests")
    print("=" * 60)
    
    tests = [
        ("State Machine", test_order_state_machine),
        ("Validation", test_order_validation),
        ("Order Agent", test_order_agent),
        ("Persistence", test_order_persistence),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n{name} test FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(success for _, success in results)
    print("\n" + ("All tests PASSED!" if all_passed else "Some tests FAILED!"))
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
