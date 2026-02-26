#!/usr/bin/env python3
"""Debug the intelligent agent"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.intelligent_order_agent import IntelligentOrderAgent


async def test():
    agent = IntelligentOrderAgent()
    session_id = "test-session"
    
    print("Testing Intelligent Agent with Debug:")
    print("="*60)
    
    # Step 1: Add wings
    print("\n1. Customer: '10 wings'")
    context = agent.get_or_create_context(session_id)
    
    decision = await agent._llm_decide("10 wings", context)
    print(f"   Decision: {decision}")
    
    observation = await agent._execute_actions(decision, context)
    print(f"   Observation: {observation}")
    
    response = await agent._llm_generate_response("10 wings", decision, observation, context)
    print(f"   Response: {response}")
    print(f"   Order after: {context.current_order}")
    
    # Step 2: Add flavor
    print("\n2. Customer: 'lemon pepper'")
    decision = await agent._llm_decide("lemon pepper", context)
    print(f"   Decision: {decision}")
    
    observation = await agent._execute_actions(decision, context)
    print(f"   Observation: {observation}")
    
    response = await agent._llm_generate_response("lemon pepper", decision, observation, context)
    print(f"   Response: {response}")
    print(f"   Order after: {context.current_order}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test())
