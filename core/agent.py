"""ReAct Agent - Main orchestrator for VoixAI v2.0"""
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from groq import Groq

from .understanding import UnderstandingEngine, UnderstandingResult
from .reasoning import ReasoningEngine, ReActStep, ConversationContext
from .generation import ResponseGenerator, ResponseStyle
from .memory import MemoryManager, WorkingMemory
from .tools import (
    search_menu, calculate_price, validate_order, suggest_upsell,
    create_ticket, escalate_to_human, get_order_status,
    MenuManager, PricingEngine, TicketManager
)


@dataclass
class AgentResponse:
    """Complete agent response"""
    text: str
    audio: bytes = None
    order_data: Dict = field(default_factory=dict)
    tool_calls: List[Dict] = field(default_factory=list)
    latency_ms: Dict = field(default_factory=dict)


class ReActAgent:
    """
    ReAct (Reasoning + Acting) Agent for Wingstop ordering.
    
    Flow:
    1. UNDERSTAND: Extract intent, entities, sentiment
    2. REASON: Decide what to do (plan + tool selection)
    3. ACT: Execute tools
    4. GENERATE: Create natural response
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the agent"""
        self.config = config
        
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=api_key)
        self.model = config.get("model", "llama-3.3-70b-versatile")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 150)
        
        # Initialize components
        self.understanding = UnderstandingEngine()
        self.reasoning = ReasoningEngine()
        self.generator = ResponseGenerator()
        self.memory = MemoryManager()
        
        # Tool registry
        self.tools = {
            "search_menu": search_menu,
            "calculate_price": calculate_price,
            "validate_order": validate_order,
            "suggest_upsell": suggest_upsell,
            "create_ticket": create_ticket,
            "escalate_to_human": escalate_to_human,
            "get_order_status": get_order_status,
        }
        
        # Shared tool dependencies
        self.menu_manager = MenuManager()
        self.pricing_engine = PricingEngine()
        self.ticket_manager = TicketManager()
        
        # State tracking per session
        self.session_contexts: Dict[str, ConversationContext] = {}
        self.session_current_items: Dict[str, Dict] = {}
        
    def _get_session_context(self, session_id: str) -> ConversationContext:
        """Get or create context for a session"""
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = ConversationContext()
            self.session_current_items[session_id] = {}
        return self.session_contexts[session_id]
        
    def process(self, user_text: str, session_id: str = None) -> Tuple[str, Dict]:
        """
        Main entry point for processing user input.
        Returns (response_text, order_data)
        """
        import time
        start_time = time.time()
        
        # Get or create session
        if not session_id:
            session_id = "default"
        
        memory = self.memory.get_memory(session_id)
        context = self._get_session_context(session_id)
        current_item = self.session_current_items[session_id]
        
        # STEP 1: UNDERSTAND
        t1 = time.time()
        understanding = self.understanding.understand(
            user_text, 
            conversation_history=memory.turns
        )
        understand_time = (time.time() - t1) * 1000
        
        # Add turn to memory
        self.memory.add_turn(
            session_id, 
            "user", 
            user_text, 
            understanding.intent.primary
        )
        
        # STEP 2: REASON - pass session-specific context
        t2 = time.time()
        react_step = self.reasoning.reason(
            understanding.to_dict(),
            context=context,
            current_item=current_item,
            history=memory.turns
        )
        reason_time = (time.time() - t2) * 1000
        
        # STEP 3: ACT (Execute tools)
        t3 = time.time()
        tool_results = self._execute_tools(react_step.tool_calls)
        act_time = (time.time() - t3) * 1000
        
        # Update context with tool results
        react_step.observation = self._format_observations(tool_results)
        
        # STEP 4: GENERATE
        t4 = time.time()
        response_text = self._generate_response(
            understanding.to_dict(),
            react_step,
            context,
            tool_results
        )
        generate_time = (time.time() - t4) * 1000
        
        # Update memory
        self.memory.add_turn(session_id, "assistant", response_text)
        
        # Update order state
        order_data = self._build_order_data(session_id, context, current_item, react_step, tool_results)
        
        # Update working memory
        self._update_working_memory(session_id, context, understanding, react_step, order_data)
        
        total_time = (time.time() - start_time) * 1000
        
        # Log latencies
        order_data["latency"] = {
            "understand_ms": int(understand_time),
            "reason_ms": int(reason_time),
            "act_ms": int(act_time),
            "generate_ms": int(generate_time),
            "total_ms": int(total_time)
        }
        
        return response_text, order_data
    
    def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute tool calls and return results"""
        results = []
        
        for call in tool_calls:
            tool_name = call.get("tool")
            params = call.get("params", {})
            
            if tool_name in self.tools:
                try:
                    # Inject dependencies if needed
                    if tool_name == "search_menu":
                        params["menu_manager"] = self.menu_manager
                    elif tool_name == "create_ticket":
                        params["ticket_manager"] = self.ticket_manager
                    
                    result = self.tools[tool_name](**params)
                    results.append({
                        "tool": tool_name,
                        "result": result,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "tool": tool_name,
                        "error": str(e),
                        "success": False
                    })
        
        return results
    
    def _format_observations(self, tool_results: List[Dict]) -> str:
        """Format tool results as observation text"""
        observations = []
        
        for result in tool_results:
            if result.get("success"):
                tool_name = result["tool"]
                data = result.get("result", {})
                
                if tool_name == "search_menu":
                    items = data.get("results", [])
                    if items:
                        item_names = [i["name"] for i in items[:3]]
                        observations.append(f"Found menu items: {', '.join(item_names)}")
                
                elif tool_name == "calculate_price":
                    total = data.get("total", 0)
                    savings = data.get("savings", 0)
                    obs = f"Total price: ${total:.2f}"
                    if savings > 0:
                        obs += f" (saves ${savings:.2f})"
                    observations.append(obs)
                
                elif tool_name == "validate_order":
                    if data.get("valid"):
                        observations.append("Order is valid")
                    else:
                        observations.append(f"Order issues: {', '.join(data.get('errors', []))}")
                
                elif tool_name == "create_ticket":
                    ticket_id = data.get("ticket_id", "")
                    observations.append(f"Created ticket: {ticket_id}")
            
            else:
                observations.append(f"Tool {result['tool']} failed: {result.get('error', '')}")
        
        return "; ".join(observations) if observations else "No tools executed"
    
    def _generate_response(self, understanding: Dict, 
                          react_step: ReActStep,
                          context: ConversationContext,
                          tool_results: List[Dict]) -> str:
        """Generate response using LLM for natural conversation"""
        
        # Use LLM for all responses to get natural, varied conversation
        return self._generate_llm_response(understanding, react_step, context, tool_results)
    
    def _generate_llm_response(self, understanding: Dict, 
                               react_step: ReActStep,
                               context: ConversationContext,
                               tool_results: List[Dict]) -> str:
        """Generate natural response using LLM with menu knowledge"""
        
        # Build state description
        state_parts = []
        if context.customer_name:
            state_parts.append(f"Customer: {context.customer_name}")
        if context.has_wing_qty:
            state_parts.append(f"Quantity: {context.current_order.get('items', [{}])[-1].get('qty', '?') if context.current_order.get('items') else '?'}")
        if context.has_wing_type:
            state_parts.append(f"Type: {context.current_order.get('items', [{}])[-1].get('modifiers', {}).get('type', '?') if context.current_order.get('items') else '?'}")
        if context.has_flavor:
            state_parts.append(f"Has flavor: yes")
        if context.is_combo:
            state_parts.append("Combo: yes")
        
        state_str = " | ".join(state_parts) if state_parts else "Starting new order"
        
        # Build menu knowledge from tool results
        menu_info = ""
        price_info = ""
        
        for result in tool_results:
            if result.get("success"):
                if result["tool"] == "search_menu":
                    items = result["result"].get("results", [])
                    if items:
                        menu_info = "AVAILABLE ITEMS:\n"
                        for item in items[:5]:
                            name = item.get('name', '')
                            desc = item.get('description', '')
                            heat = item.get('heat_level', 0)
                            popular = " ⭐POPULAR" if item.get('popular') else ""
                            heat_str = "🔥" * heat if heat > 0 else "Mild"
                            menu_info += f"- {name}{popular}: {desc} [{heat_str}]\n"
                
                elif result["tool"] == "calculate_price":
                    data = result["result"]
                    price_info = f"Total: ${data.get('total', 0):.2f}"
                    if data.get('savings', 0) > 0:
                        price_info += f" (Save ${data.get('savings', 0):.2f}!)"
        
        # Determine what user wants vs what we need
        user_query = understanding.get("raw_text", "").lower()
        is_menu_question = any(w in user_query for w in ["flavor", "what do you have", "menu", "recommend", "suggest", "spicy", "mild"])
        is_price_question = any(w in user_query for w in ["price", "cost", "how much"])
        
        # Build the prompt
        system_prompt = f"""You are Tasha, a friendly, energetic Wingstop cashier. Respond naturally like you're talking to a friend.

CUSTOMER: {context.customer_name or "New customer"}
ORDER PROGRESS: {state_str}

{menu_info}
{price_info}

FULL MENU:
FLAVORS:
- Mild: Lemon Pepper (our #1 seller!), Garlic Parmesan, Hickory BBQ, Louisiana Rub
- Medium: Cajun, Original Hot, Korean BBQ
- Hot: Mango Habanero (sweet heat), Spicy Korean
- Extreme: Atomic (nuclear hot!)

OTHER: Bone-in or Boneless wings. Combos include fries + drink. Sides: fries, veggie sticks. Drinks: Coke, Sprite, Dr Pepper, Lemonade.

YOUR JOB:
1. FIRST - Answer their question if they asked one (flavors, prices, recommendations)
2. THEN - Guide them to the next step in ordering
3. Be conversational, not robotic. Use contractions. Be friendly.
4. Keep it SHORT - 5 to 15 words max.
5. Use their name if you know it.

RULES:
- NEVER say "As an AI" or robotic phrases
- NEVER list everything - pick 2-3 relevant things
- If asking for quantity: "How many wings?"
- If asking for type: "Bone-in or boneless?"
- If suggesting flavors: "Lemon Pepper's our #1, or try Mango Habanero if you like heat"

They said: "{user_query}"

RESPOND NATURALLY:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": understanding.get("raw_text", "")}
                ],
                temperature=0.8,
                max_tokens=60
            )
            
            text = response.choices[0].message.content or "What was that?"
            return self._clean_response(text)
            
        except Exception as e:
            print(f"[Agent] LLM error: {e}")
            return "What was that?"
    
    def _clean_response(self, text: str) -> str:
        """Clean LLM response"""
        if not text:
            return "What was that?"
        
        text = text.strip().strip('"').strip("'")
        
        # Remove forbidden phrases
        forbidden = ["as an ai", "i'm sorry", "i apologize", "unfortunately", 
                     "however", "furthermore", "moreover", "please note"]
        text_lower = text.lower()
        for phrase in forbidden:
            if phrase in text_lower:
                return "What was that?"
        
        return text
    
    def _build_order_data(self, session_id: str, context: ConversationContext, 
                          current_item: Dict,
                          react_step: ReActStep, 
                          tool_results: List[Dict]) -> Dict:
        """Build order data from current state"""
        memory = self.memory.get_memory(session_id)
        
        order_data = {
            "items": context.current_order.get("items", []),
            "state": self._get_stage_from_action(react_step.action),
            "order_complete": react_step.action == "complete_order",
            "customer_name": context.customer_name,
            "total_price": 0.0,
            # Include building state for debugging
            "building_state": {
                "has_name": context.has_name,
                "has_wing_qty": context.has_wing_qty,
                "has_wing_type": context.has_wing_type,
                "has_flavor": context.has_flavor,
                "combo_decided": context.combo_decided,
                "is_combo": context.is_combo,
                "current_item": current_item,
            }
        }
        
        # Get price from tool results
        for result in tool_results:
            if result.get("tool") == "calculate_price" and result.get("success"):
                order_data["total_price"] = result["result"].get("total", 0)
        
        return order_data
    
    def _update_working_memory(self, session_id: str, 
                               context: ConversationContext,
                               understanding: UnderstandingResult,
                               react_step: ReActStep,
                               order_data: Dict):
        """Update working memory with new information"""
        updates = {
            "conversation_stage": self._get_stage_from_action(react_step.action),
            "last_intent": understanding.intent.primary,
            "current_order": order_data,
            "customer_name": context.customer_name,
            "has_name": context.has_name,
            "has_wing_qty": context.has_wing_qty,
            "has_wing_type": context.has_wing_type,
            "has_flavor": context.has_flavor,
        }
        
        self.memory.update_memory(session_id, updates)
    
    def _get_stage_from_action(self, action: str) -> str:
        """Map action to conversation stage"""
        stage_map = {
            "greet": "greeting",
            "ask_name": "greeting",
            "ask_wing_qty": "discovery",
            "ask_wing_type": "discovery",
            "ask_flavor": "building",
            "ask_combo": "building",
            "ask_drink": "building",
            "ask_side": "building",
            "ask_dip": "building",
            "confirm_item": "building",
            "confirm_order": "confirming",
            "complete_order": "closing",
            "upsell": "building",
            "ask_preference": "discovery",
            "suggest_items": "discovery",
            "ask_clarification": "discovery",
        }
        return stage_map.get(action, "building")
    
    def _get_order_summary(self, context: ConversationContext) -> str:
        """Get human-readable order summary"""
        items = context.current_order.get("items", [])
        if not items:
            return "nothing yet"
        
        parts = []
        for item in items:
            name = item.get("name", "item")
            qty = item.get("qty", 1)
            parts.append(f"{qty} {name}")
        
        return ", ".join(parts)
    
    def get_order_summary_dict(self, session_id: str) -> Dict:
        """Get complete order summary for UI"""
        memory = self.memory.get_memory(session_id)
        context = self._get_session_context(session_id)
        
        return {
            "state": memory.conversation_stage,
            "order_text": self._get_order_summary(context),
            "items": context.current_order.get("items", []),
            "customer_name": context.customer_name,
            "total_price": context.current_order.get("total", 0),
            "preferences": memory.customer_preferences
        }
    
    def reset(self, session_id: str = None):
        """Reset agent state"""
        if session_id:
            self.memory.clear_session(session_id)
            if session_id in self.session_contexts:
                del self.session_contexts[session_id]
            if session_id in self.session_current_items:
                del self.session_current_items[session_id]
        else:
            # Clear all sessions
            self.memory.working_memory.clear()
            self.session_contexts.clear()
            self.session_current_items.clear()
    
    def create_order_in_db(self, session_id: str) -> int:
        """Create new order in database"""
        return self.memory.create_order(session_id)
