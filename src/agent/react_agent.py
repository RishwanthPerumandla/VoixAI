"""
ReAct Agent - Core reasoning engine
Phase 1.6: Basic implementation with 2 tools
"""

import json
from typing import Any, Dict, List, Optional
from groq import Groq

from src.config import settings
from src.tools.registry import ToolRegistry
from src.memory.working_memory import WorkingMemory
from src.memory.short_term_memory import ShortTermMemory


class ReActAgent:
    """
    ReAct Agent: Reasoning + Acting
    
    Phase 1.6: Basic implementation with 2 tools:
    - search_menu
    - create_order
    """
    
    def __init__(self):
        self.llm = Groq(api_key=settings.groq_api_key)
        self.tools = ToolRegistry().create_default_registry()
        self.working_memory = WorkingMemory(capacity=5)
        self.short_term_memory = ShortTermMemory()
        
        # System prompt for the agent
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with tool descriptions"""
        tool_schemas = self.tools.get_all_schemas()
        
        return f"""You are Tasha, a friendly Wingstop cashier taking phone orders.
Your job is to help customers order wings, sides, drinks, and dips.

PERSONALITY:
- Friendly, efficient, knowledgeable
- Use contractions ("I'm", "don't", "let's")
- Keep responses under 15 words for speed
- Be slightly playful but professional

AVAILABLE TOOLS:
{json.dumps(tool_schemas, indent=2)}

INSTRUCTIONS:
1. Understand what the customer wants
2. Use tools when needed (search_menu, create_order)
3. Respond naturally and concisely
4. Confirm order details before finalizing

Current conversation:
"""
    
    async def process(self, user_message: str, session_id: str) -> str:
        """
        Process user message and generate response
        
        Args:
            user_message: Transcribed text from user
            session_id: Unique session identifier
            
        Returns:
            Response text to be spoken
        """
        # Add user message to working memory
        self.working_memory.add_turn("user", user_message)
        
        # Build context for LLM
        context = self.working_memory.get_context_for_prompt()
        
        # Determine if we need to use a tool
        tool_result = await self._maybe_use_tool(user_message)
        
        # Generate response
        response = await self._generate_response(
            user_message=user_message,
            context=context,
            tool_result=tool_result
        )
        
        # Add assistant response to working memory
        self.working_memory.add_turn("assistant", response)
        
        # Persist to short-term memory
        await self._persist_session(session_id)
        
        return response
    
    async def _maybe_use_tool(self, message: str) -> Optional[Dict]:
        """
        Determine if a tool should be used and execute it
        Phase 1.6: Simple keyword matching, will be enhanced later
        """
        message_lower = message.lower()
        
        # Check for menu search intent
        if any(word in message_lower for word in ["menu", "have", "flavor", "wing", "side", "drink"]):
            if "order" not in message_lower or "like to order" in message_lower:
                # Extract search query
                query = message_lower.replace("do you have", "").replace("what", "").strip()
                result = await self.tools.execute("search_menu", {"query": query})
                if result.success:
                    return {"tool": "search_menu", "data": result.data}
        
        # Check for order creation intent
        if any(phrase in message_lower for phrase in ["that's all", "complete order", "place order", "i'm done"]):
            current_order = self.working_memory.get_current_order()
            if current_order:
                customer_info = self.working_memory.get_customer_info()
                result = await self.tools.execute("create_order", {
                    "customer_name": customer_info.get("name", "Guest"),
                    "items": current_order.get("items", []),
                    "conversation_id": "temp-id"
                })
                if result.success:
                    return {"tool": "create_order", "data": result.data}
        
        return None
    
    async def _generate_response(
        self, 
        user_message: str,
        context: str,
        tool_result: Optional[Dict] = None
    ) -> str:
        """Generate natural language response"""
        
        # Build prompt
        prompt = self.system_prompt + context + "\n\n"
        
        if tool_result:
            prompt += f"[Tool used: {tool_result['tool']}]\n"
            prompt += f"[Result: {json.dumps(tool_result['data'])}]\n\n"
        
        prompt += f"Customer: {user_message}\nAssistant:"
        
        # Call LLM
        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,  # Keep it short for speed
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Fallback response
            return "Sorry, I'm having a bit of trouble. Could you repeat that?"
    
    async def _persist_session(self, session_id: str):
        """Persist session to short-term memory"""
        session_data = {
            "working_memory": {
                "turns": self.working_memory.get_recent(),
                "current_order": self.working_memory.get_current_order()
            },
            "customer_info": self.working_memory.get_customer_info()
        }
        await self.short_term_memory.save_session(session_id, session_data)
    
    async def load_session(self, session_id: str):
        """Load session from short-term memory"""
        session_data = await self.short_term_memory.get_session(session_id)
        if session_data:
            wm_data = session_data.get("working_memory", {})
            for turn in wm_data.get("turns", []):
                self.working_memory.add_turn(turn["role"], turn["content"])
            self.working_memory.set_current_order(wm_data.get("current_order"))
            self.working_memory.set_customer_info(session_data.get("customer_info", {}))
