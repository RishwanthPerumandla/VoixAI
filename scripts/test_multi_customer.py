#!/usr/bin/env python3
"""
Test Multi-Customer Workflow
Demonstrates sequential customer ordering
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orders.session_manager import OrderSessionManager, MultiCustomerAgent
from src.orders.order_agent import OrderCentricAgent


async def test_session_manager():
    """Test session lifecycle"""
    print("\n=== Testing Session Manager ===")
    
    manager = OrderSessionManager()
    
    # Customer 1: Rishi
    print("\n--- Customer 1: Rishi ---")
    session1 = manager.start_new_session(customer_name="Rishi")
    print(f"Session started: {session1.session_id}")
    
    # Simulate order
    order = manager.get_current_order()
    from src.orders.state_machine import OrderItem
    item = OrderItem(
        id="item_0", name="Boneless Wings", category="wings",
        quantity=10, unit_price=1.29, flavor="Lemon Pepper"
    )
    order.add_item(item)
    order.set_customer_info(name="Rishi", phone="555-0001")
    order.transition_to(OrderState.CONFIRMED)
    
    print(f"Order created: {order.id[:8]}")
    print(f"Total: ${order.total:.2f}")
    
    # Complete order
    manager.complete_order(order)
    print(f"Order completed for Rishi")
    
    # Reset for next customer
    print("\n--- Resetting for next customer ---")
    session2 = manager.reset_for_next_customer()
    
    # Customer 2: Sarah
    print("\n--- Customer 2: Sarah ---")
    session2 = manager.start_new_session(customer_name="Sarah")
    print(f"Session started: {session2.session_id}")
    
    order2 = manager.get_current_order()
    item2 = OrderItem(
        id="item_0", name="Bone-In Wings", category="wings",
        quantity=15, unit_price=1.19, flavor="Garlic Parmesan"
    )
    order2.add_item(item2)
    order2.set_customer_info(name="Sarah")
    order2.transition_to(OrderState.CONFIRMED)
    
    print(f"Order created: {order2.id[:8]}")
    print(f"Total: ${order2.total:.2f}")
    
    # Check stats
    print("\n--- Daily Stats ---")
    stats = manager.get_daily_stats()
    print(f"Total sessions: {stats['total_sessions']}")
    print(f"Completed orders: {stats['completed_orders']}")
    print(f"Total revenue: ${stats['total_revenue']:.2f}")
    
    print("\nSession Manager test: PASSED")
    return True


async def test_multi_customer_agent():
    """Test the full multi-customer agent"""
    print("\n=== Testing Multi-Customer Agent ===")
    
    order_agent = OrderCentricAgent()
    agent = MultiCustomerAgent(order_agent)
    
    # Customer 1: Rishi
    print("\n--- Customer 1: Rishi ---")
    
    responses = []
    messages = [
        "Hi, I'd like to order",
        "My name is Rishi",
        "I want 10 boneless wings",
        "Lemon pepper flavor",
        "That's all",
        "Yes, confirm the order"
    ]
    
    for msg in messages:
        response = await agent.process(msg)
        responses.append((msg, response))
        print(f"  Rishi: {msg}")
        print(f"  Agent: {response[:100]}...")
        print()
    
    # Signal order complete
    print("--- Order Complete ---")
    response = await agent.process("Order complete")
    print(f"Agent: {response}")
    
    # Next customer
    print("\n--- Customer 2: Sarah ---")
    response = await agent.process("Next customer please")
    print(f"Agent: {response}")
    
    messages2 = [
        "Hi, I'm Sarah",
        "Can I get 15 bone-in wings with garlic parmesan?",
        "That's it",
        "Yes place the order"
    ]
    
    for msg in messages2:
        response = await agent.process(msg)
        print(f"  Sarah: {msg}")
        print(f"  Agent: {response[:100]}...")
        print()
    
    # Check status
    print("\n--- Final Status ---")
    status = agent.get_status()
    print(f"Daily stats: {status['daily_stats']}")
    
    print("\nMulti-Customer Agent test: PASSED")
    return True


async def test_auto_reset():
    """Test automatic session handling"""
    print("\n=== Testing Auto Session Handling ===")
    
    manager = OrderSessionManager()
    
    # First customer automatically starts
    print("\nFirst message comes in...")
    session = manager.get_or_create_session(customer_name="Customer 1")
    print(f"Auto-started session: {session.session_id}")
    
    # Complete order
    order = manager.get_current_order()
    from src.orders.state_machine import OrderItem
    item = OrderItem(
        id="item_0", name="Wings", category="wings",
        quantity=10, unit_price=1.29
    )
    order.add_item(item)
    order.set_customer_info(name="Customer 1")
    order.transition_to(OrderState.CONFIRMED)
    manager.complete_order(order)
    
    print(f"Order completed")
    
    # Next customer comes in (should auto-reset)
    print("\nNext customer arrives...")
    session2 = manager.get_or_create_session(customer_name="Customer 2")
    print(f"New session: {session2.session_id}")
    print(f"Previous session archived: {len(manager.completed_sessions)} in history")
    
    print("\nAuto-reset test: PASSED")
    return True


async def main():
    """Run all multi-customer tests"""
    print("=" * 60)
    print("Multi-Customer Order System Tests")
    print("=" * 60)
    
    tests = [
        ("Session Manager", test_session_manager),
        ("Multi-Customer Agent", test_multi_customer_agent),
        ("Auto Reset", test_auto_reset),
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
    # Import here to avoid issues
    from src.orders.state_machine import OrderState
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
