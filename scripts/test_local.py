"""
Local testing script for VoixAI v3.0
Tests basic functionality without Daily.co
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.react_agent import ReActAgent
from src.memory.working_memory import WorkingMemory
from src.memory.short_term_memory import ShortTermMemory
from src.tools.registry import ToolRegistry


async def test_tools():
    """Test tool registry"""
    print("\n🧪 Testing Tool Registry...")
    
    registry = ToolRegistry().create_default_registry()
    
    # List available tools
    tools = registry.list_tools()
    print(f"   Available tools: {tools}")
    
    # Test menu search
    print("\n   Testing search_menu...")
    result = await registry.execute("search_menu", {"query": "wings"})
    print(f"   Success: {result.success}")
    if result.success:
        print(f"   Found {result.data['count']} results")
    
    # Test order creation
    print("\n   Testing create_order...")
    result = await registry.execute("create_order", {
        "customer_name": "Test Customer",
        "items": [
            {"name": "Boneless Wings", "quantity": 10, "price": 11.99}
        ]
    })
    print(f"   Success: {result.success}")
    if result.success:
        print(f"   Order ID: {result.data['order_id']}")
        print(f"   Total: ${result.data['total']}")


async def test_memory():
    """Test memory systems"""
    print("\n🧪 Testing Memory Systems...")
    
    # Working memory
    print("\n   Testing WorkingMemory...")
    wm = WorkingMemory(capacity=5)
    wm.add_turn("user", "Hi, I'd like to order wings")
    wm.add_turn("assistant", "Sure! Bone-in or boneless?")
    wm.add_turn("user", "Boneless please")
    
    recent = wm.get_recent(2)
    print(f"   Recent turns: {len(recent)}")
    print(f"   Context:\n{wm.get_context_for_prompt()}")
    
    # Short-term memory (Redis)
    print("\n   Testing ShortTermMemory...")
    stm = ShortTermMemory()
    
    try:
        await stm.connect()
        await stm.save_session("test-session", {
            "customer": "Test",
            "order": {"items": []}
        })
        
        data = await stm.get_session("test-session")
        print(f"   Session saved and retrieved: {data is not None}")
        
        await stm.delete_session("test-session")
        await stm.disconnect()
    except Exception as e:
        print(f"   ⚠️  Redis not available: {e}")
        print("   Make sure: docker-compose up -d redis")


async def test_agent():
    """Test ReAct agent"""
    print("\n🧪 Testing ReAct Agent...")
    
    try:
        agent = ReActAgent()
        print("   Agent initialized")
        
        # Test message processing
        print("\n   Testing message processing...")
        
        test_messages = [
            "Hi, I'd like to order some wings",
            "What flavors do you have?",
            "I'll take 10 boneless with Lemon Pepper",
        ]
        
        for msg in test_messages:
            print(f"\n   User: {msg}")
            response = await agent.process(msg, session_id="test-session")
            print(f"   Tasha: {response}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 VoixAI v3.0 - Local Testing")
    print("=" * 60)
    
    try:
        await test_tools()
        await test_memory()
        await test_agent()
        
        print("\n" + "=" * 60)
        print("✅ Tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
