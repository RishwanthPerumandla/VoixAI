#!/usr/bin/env python3
"""Test database interface"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import get_memory_manager


async def test():
    print("Testing Database Interface...")
    print("=" * 50)
    
    try:
        manager = await get_memory_manager()
        
        # Start conversation
        session_id = 'test-session-123'
        result = await manager.start_conversation(session_id, 'Test Customer')
        conv_id = result['conversation_id'][:8]
        print(f"Started conversation: {conv_id}...")
        
        # Add messages
        await manager.add_message(session_id, 'user', 'I want 10 boneless wings')
        await manager.add_message(session_id, 'assistant', 'Sure! What flavor?')
        print("Added messages to conversation")
        
        # Get context
        context = manager.get_context(session_id)
        print(f"Context has {len(context.split(chr(10)))} lines")
        
        # Clean up
        await manager.end_conversation(session_id)
        print("\nDatabase test passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
