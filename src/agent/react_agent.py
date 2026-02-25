"""
Proper ReAct Agent
Uses LLM for reasoning, tool selection, and response generation
"""

import json
import re
from typing import Any, Dict, List, Optional
from groq import Groq
from dataclasses import dataclass, field

from src.config import settings
from src.tools.registry import ToolRegistry
from src.memory.working_memory import WorkingMemory
from src.memory.short_term_memory import ShortTermMemory


@dataclass
class ConversationState:
    """Track conversation state"""
    customer_name: Optional[str] = None
    items: List[Dict] = field(default_factory=list)
    order_type: Optional[str] = None  # pickup/delivery
    stage: str = "greeting"  # greeting, ordering, confirming, completed
    confirmed: bool = False


class ReActAgent:
    """
    True ReAct Agent:
    1. OBSERVE: Get user input + context
    2. REASON: Use LLM to understand intent and plan
    3. ACT: Execute tools if needed
    4. GENERATE: Use LLM to create natural response
    """
    
    def __init__(self):
        self.llm = Groq(api_key=settings.groq_api_key)
        self.tools = ToolRegistry().create_default_registry()
        self.working_memory = WorkingMemory(capacity=20)
        self.short_term_memory = ShortTermMemory()
    
    async def process(self, user_message: str, session_id: str) -> str:
        """Main ReAct loop"""
        
        # Load session
        await self.load_session(session_id)
        
        # Add to memory
        self.working_memory.add_turn("user", user_message)
        
        # REASON: Understand intent and extract entities
        understanding = await self._understand(user_message)
        print(f"[Agent] Understanding: {understanding}")
        
        # Update state based on understanding
        self._update_state(understanding)
        
        # ACT: Use tools if needed
        tool_results = await self._act(understanding)
        
        # GENERATE: Create response
        response = await self._generate(understanding, tool_results)
        
        # Save to memory
        self.working_memory.add_turn("assistant", response)
        await self._persist_session(session_id)
        
        return response
    
    async def _understand(self, message: str) -> Dict:
        """
        REASON step: Use LLM to understand user intent
        """
        state = self._get_state()
        context = self._get_context()
        
        prompt = f"""You are analyzing a customer service conversation for Wingstop.

CURRENT CONVERSATION STATE:
{json.dumps(state, indent=2)}

CONVERSATION HISTORY:
{context}

USER JUST SAID: "{message}"

Analyze this message and extract:
1. Intent (greeting, provide_name, order_items, ask_question, modify_order, confirm, decline, complete_order)
2. Entities extracted (name, items, quantities, flavors, preferences)
3. What information is being conveyed
4. What might be missing

Respond in JSON format:
{{
    "intent": "...",
    "entities": {{
        "name": "...",
        "items": [{{"name": "...", "quantity": N, "modifiers": {{}}}}],
        "preferences": [],
        "questions": []
    }},
    "information_conveyed": "...",
    "missing_info": ["..."],
    "confidence": 0.0-1.0
}}"""
        
        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a conversation analyzer. Extract intent and entities accurately."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"[Agent] Understanding error: {e}")
            return {
                "intent": "unknown",
                "entities": {},
                "confidence": 0.5
            }
    
    async def _act(self, understanding: Dict) -> List[Dict]:
        """
        ACT step: Execute tools based on understanding
        """
        results = []
        intent = understanding.get("intent", "")
        entities = understanding.get("entities", {})
        
        # Use tools based on intent
        if intent == "order_items" and entities.get("items"):
            # Calculate price
            items = entities["items"]
            for item in items:
                item["unit_price"] = self._get_item_price(item.get("name", ""))
            
            price_result = await self.tools.execute("calculate_price", {
                "items": items,
                "apply_combo_discount": True
            })
            results.append({"tool": "calculate_price", "result": price_result})
            
            # Check for upsells
            upsell_result = await self.tools.execute("suggest_upsell", {
                "current_items": items
            })
            results.append({"tool": "suggest_upsell", "result": upsell_result})
        
        if intent == "ask_question" and "menu" in str(entities.get("questions", [])).lower():
            # Search menu
            query = " ".join(entities.get("questions", []))
            menu_result = await self.tools.execute("search_menu", {
                "query": query,
                "use_semantic": True
            })
            results.append({"tool": "search_menu", "result": menu_result})
        
        if intent == "complete_order":
            # Validate order
            order = self._get_state()
            validate_result = await self.tools.execute("validate_order", {
                "order": order
            })
            results.append({"tool": "validate_order", "result": validate_result})
        
        return results
    
    async def _generate(self, understanding: Dict, tool_results: List[Dict]) -> str:
        """
        GENERATE step: Use LLM to create natural response
        """
        state = self._get_state()
        context = self._get_context()
        
        # Build system prompt
        system_prompt = """You are Tasha, a friendly and efficient Wingstop cashier.

PERSONALITY:
- Warm, welcoming, and knowledgeable about wings
- Use casual, conversational language with contractions
- Remember customer details and reference them naturally
- Be helpful but concise (1-2 sentences)
- Show personality - be slightly playful

IMPORTANT RULES:
- ALWAYS use the customer's name if you know it
- Acknowledge what the customer just said
- Build on the conversation history, don't repeat
- Guide the conversation naturally toward completing the order
- If they said "that's it" or similar, confirm their order and ask pickup/delivery
- Never ask for info they already provided

CONVERSATION FLOW:
1. Get name first
2. Take order (wings → type → flavor → extras)
3. Confirm when they say they're done
4. Ask pickup/delivery
5. Complete order"""
        
        # Build context for LLM
        prompt = f"""CURRENT ORDER STATE:
{json.dumps(state, indent=2)}

CONVERSATION HISTORY:
{context}

USER UNDERSTANDING:
{json.dumps(understanding, indent=2)}

TOOL RESULTS:
{json.dumps([r.get("result", {}).data if hasattr(r.get("result"), "data") else r for r in tool_results], indent=2, default=str)}

Generate a natural response as Tasha:"""
        
        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[Agent] Generation error: {e}")
            # Fallback response
            if not state.get("customer_name"):
                return "Hey there! I'm Tasha. What's your name?"
            return f"Hey {state['customer_name']}! What can I get you?"
    
    def _update_state(self, understanding: Dict):
        """Update conversation state based on understanding"""
        entities = understanding.get("entities", {})
        intent = understanding.get("intent", "")
        
        # Get current state
        state = self._get_state()
        
        # Update name
        if entities.get("name") and not state["customer_name"]:
            state["customer_name"] = entities["name"]
        
        # Update items
        if entities.get("items"):
            for new_item in entities["items"]:
                # Check if item already exists
                existing = False
                for existing_item in state["items"]:
                    if existing_item.get("name") == new_item.get("name"):
                        # Update quantity or other fields
                        if new_item.get("quantity"):
                            existing_item["quantity"] = new_item["quantity"]
                        if new_item.get("flavor"):
                            existing_item["flavor"] = new_item["flavor"]
                        existing = True
                        break
                
                if not existing:
                    state["items"].append(new_item)
        
        # Update stage based on intent
        if intent == "greeting":
            state["stage"] = "greeting"
        elif intent == "provide_name":
            state["stage"] = "ordering"
        elif intent == "order_items":
            state["stage"] = "ordering"
        elif intent == "complete_order":
            state["stage"] = "confirming"
        elif intent == "confirm":
            if state["stage"] == "confirming":
                state["confirmed"] = True
                state["stage"] = "completed"
        
        # Save state
        self.working_memory.set_customer_info({"name": state["customer_name"]})
        self.working_memory.set_current_order({
            "items": state["items"],
            "order_type": state["order_type"],
            "stage": state["stage"],
            "confirmed": state["confirmed"]
        })
    
    def _get_state(self) -> Dict:
        """Get current conversation state"""
        customer = self.working_memory.get_customer_info() or {}
        order = self.working_memory.get_current_order() or {}
        
        return {
            "customer_name": customer.get("name"),
            "items": order.get("items", []),
            "order_type": order.get("order_type"),
            "stage": order.get("stage", "greeting"),
            "confirmed": order.get("confirmed", False)
        }
    
    def _get_context(self) -> str:
        """Get conversation context"""
        turns = self.working_memory.get_recent(10)
        context = []
        for turn in turns:
            role = "Customer" if turn["role"] == "user" else "Tasha"
            context.append(f"{role}: {turn['content']}")
        return "\n".join(context)
    
    def _get_item_price(self, item_name: str) -> float:
        """Get price for menu item"""
        prices = {
            "wings": 11.99,
            "boneless wings": 11.99,
            "classic wings": 12.99,
            "fries": 3.99,
            "cheese fries": 4.99,
            "ranch dip": 0.99,
            "blue cheese dip": 0.99,
            "drink": 2.99
        }
        
        name_lower = item_name.lower()
        for key, price in prices.items():
            if key in name_lower:
                return price
        
        return 11.99  # default
    
    async def _persist_session(self, session_id: str):
        """Save session"""
        session_data = {
            "working_memory": {
                "turns": self.working_memory.get_recent(),
                "current_order": self.working_memory.get_current_order()
            },
            "customer_info": self.working_memory.get_customer_info()
        }
        await self.short_term_memory.save_session(session_id, session_data)
    
    async def load_session(self, session_id: str):
        """Load session"""
        session_data = await self.short_term_memory.get_session(session_id)
        if session_data:
            wm_data = session_data.get("working_memory", {})
            for turn in wm_data.get("turns", []):
                self.working_memory.add_turn(turn["role"], turn["content"])
            self.working_memory.set_current_order(wm_data.get("current_order"))
            self.working_memory.set_customer_info(session_data.get("customer_info", {}))
