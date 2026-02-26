"""
Intelligent Order Agent - Pure ReAct Pattern
No state machines - just LLM reasoning + tools
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from src.config import settings
from src.tools.registry import ToolRegistry


@dataclass
class ConversationContext:
    """Simple context tracking - not state machine"""
    messages: List[Dict[str, str]]
    current_order: Optional[Dict] = None
    
    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_recent_context(self, n: int = 10) -> str:
        """Get recent conversation for LLM prompt"""
        recent = self.messages[-n:] if len(self.messages) > n else self.messages
        lines = []
        for msg in recent:
            role = "Customer" if msg["role"] == "user" else "Tasha"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)


class IntelligentOrderAgent:
    """
    Pure ReAct Agent - No hardcoded states
    Uses LLM for all reasoning, tool selection, and response generation
    """
    
    def __init__(self):
        self.tools = ToolRegistry().create_default_registry()
        self.contexts: Dict[str, ConversationContext] = {}
        self.llm_client = None
        if settings.groq_api_key:
            from groq import Groq
            self.llm_client = Groq(api_key=settings.groq_api_key)
        
        # System prompt that defines the agent's behavior
        self.system_prompt = """You are Tasha, a friendly and efficient Wingstop cashier taking phone orders.

YOUR ROLE:
- Take food orders naturally through conversation
- Help customers choose items, flavors, and sides
- Calculate totals and confirm orders
- Be helpful but concise (under 20 words when possible)

ORDER WORKFLOW:
1. Greet customer and understand what they want
2. Build their order by adding items they request
3. Ask for missing details (flavors, sizes, names)
4. Review the complete order with them
5. Confirm and place the order

TOOLS AVAILABLE:
- search_menu: Find menu items
- add_to_order: Add items to current order
- get_order_summary: Show current order details
- calculate_price: Compute totals with tax
- confirm_order: Finalize the order

RULES:
- Never mention "states" or "machines" - just have natural conversation
- If customer says "nothing", "that's all", "done" - show them the order summary
- Always get customer name before confirming
- Suggest popular flavors if customer is unsure
- Be proactive but not pushy

CURRENT ORDER CONTEXT:
{order_context}

CONVERSATION HISTORY:
{conversation_history}

Respond naturally as Tasha."""
    
    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get or create conversation context"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(
                messages=[],
                current_order={"items": [], "customer_name": None, "total": 0.0}
            )
        return self.contexts[session_id]
    
    async def process(self, user_message: str, session_id: str) -> str:
        """
        Process user message using pure LLM reasoning
        No hardcoded states - LLM decides what to do
        """
        context = self.get_or_create_context(session_id)
        context.add_message("user", user_message)
        
        # Step 1: Let LLM decide what to do (Reasoning)
        decision = await self._llm_decide(user_message, context)
        
        # Step 2: Execute actions (Act)
        observation = await self._execute_actions(decision, context)
        
        # Step 3: Generate response (Generate)
        response = await self._llm_generate_response(
            user_message, 
            decision, 
            observation, 
            context
        )
        
        context.add_message("assistant", response)
        return response
    
    async def _llm_decide(self, user_message: str, context: ConversationContext) -> Dict:
        """
        LLM decides what actions to take
        Returns structured decision, not state
        """
        if not self.llm_client:
            # Fallback for testing without LLM
            return self._fallback_decide(user_message, context)
        
        # Get available tool names
        available_tools = self.tools.list_tools()
        
        prompt = f"""Based on the customer's message, decide what to do.

Customer message: "{user_message}"

Current order: {json.dumps(context.current_order, indent=2)}

AVAILABLE TOOLS (use ONLY these):
{available_tools}

DECISION FORMAT (respond ONLY in this JSON format):
{{
    "intent": "add_item|remove_item|modify_item|get_info|confirm|done_ordering|general_chat",
    "actions": [
        {{"tool": "tool_name (must be from AVAILABLE TOOLS list)", "params": {{...}}}}
    ],
    "missing_info": ["what info is needed"],
    "response_strategy": "how to respond"
}}

DECISION:"""

        try:
            response = self.llm_client.chat.completions.create(
                model=settings.llm_model if hasattr(settings, 'llm_model') else "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an order processing assistant. Respond only in JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            # Extract JSON
            try:
                return json.loads(content)
            except:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                raise
                
        except Exception as e:
            print(f"[Agent] LLM decision error: {e}")
            return self._fallback_decide(user_message, context)
    
    def _fallback_decide(self, user_message: str, context: ConversationContext) -> Dict:
        """Simple fallback when LLM unavailable - directly manipulates order"""
        msg_lower = user_message.lower()
        order = context.current_order
        
        # Check for name first
        name = self._extract_name(user_message)
        if name:
            order["customer_name"] = name
            return {
                "intent": "provide_info",
                "actions": [],
                "missing_info": [],
                "response_strategy": "acknowledge name"
            }
        
        # Check for done/complete phrases
        if any(word in msg_lower for word in ['done', 'that\'s all', 'nothing', 'complete', 'finished', 'that\'s it']):
            return {
                "intent": "done_ordering",
                "actions": [],
                "missing_info": [] if order.get("customer_name") else ["customer_name"],
                "response_strategy": "show summary and ask for name if missing"
            }
        
        # Check for confirm
        if any(word in msg_lower for word in ['confirm', 'place', 'order it', 'yes']):
            return {
                "intent": "confirm",
                "actions": [],
                "missing_info": [],
                "response_strategy": "confirm order or explain what's missing"
            }
        
        # Check for menu items - ADD TO ORDER DIRECTLY
        if any(word in msg_lower for word in ['wing', 'fries', 'drink', 'combo']):
            items = self._parse_items_from_message(user_message)
            if items:
                order["items"].extend(items)
                # Check if flavor is missing for wings
                last_item = order["items"][-1]
                if 'wing' in last_item.get('name', '').lower() and not last_item.get('flavor'):
                    return {
                        "intent": "add_item_needs_flavor",
                        "actions": [],
                        "missing_info": ["flavor"],
                        "response_strategy": "ask for flavor"
                    }
                return {
                    "intent": "add_item",
                    "actions": [],
                    "missing_info": [],
                    "response_strategy": "acknowledge and ask for more"
                }
        
        # Check for flavor (modifying last item)
        flavors = ['lemon pepper', 'garlic parmesan', 'original hot', 'bbq', 'hickory', 'mango habanero', 'atomic']
        for flavor in flavors:
            if flavor in msg_lower:
                # Add flavor to last wing item
                if order.get("items"):
                    for item in reversed(order["items"]):
                        if 'wing' in item.get('name', '').lower() and not item.get('flavor'):
                            item['flavor'] = flavor.title()
                            return {
                                "intent": "modify_item",
                                "actions": [],
                                "missing_info": [],
                                "response_strategy": "confirm flavor and ask for more"
                            }
        
        return {
            "intent": "general_chat",
            "actions": [],
            "missing_info": [],
            "response_strategy": "helpful general response"
        }
    
    async def _execute_actions(self, decision: Dict, context: ConversationContext) -> Dict:
        """Execute the decided actions - actions already executed in _fallback_decide"""
        observations = {"results": [], "order": context.current_order}
        
        # For LLM-based decisions, execute the actions
        for action in decision.get("actions", []):
            tool_name = action.get("tool")
            params = action.get("params", {})
            
            try:
                if tool_name == "parse_order":
                    items = self._parse_items_from_message(params.get("message", ""))
                    context.current_order["items"].extend(items)
                    observations["results"].append(f"Added {len(items)} items")
                    
                elif tool_name == "get_order_summary":
                    total = sum(item.get("total", 0) for item in context.current_order["items"])
                    context.current_order["total"] = total
                    observations["results"].append(f"Order total: ${total:.2f}")
                    
                elif tool_name == "extract_customer_name":
                    name = self._extract_name(params.get("message", ""))
                    if name:
                        context.current_order["customer_name"] = name
                        observations["results"].append(f"Customer: {name}")
                
                elif tool_name:
                    # Try to use registered tool
                    try:
                        tool = self.tools.get(tool_name)
                        result = await tool.execute(**params)
                        observations["results"].append(str(result))
                    except Exception as tool_e:
                        observations["results"].append(f"Tool error: {tool_e}")
                    
            except Exception as e:
                observations["results"].append(f"Error: {e}")
        
        # Calculate total
        total = sum(item.get("total", 0) for item in context.current_order["items"])
        context.current_order["total"] = total
        
        return observations
    
    async def _llm_generate_response(self, user_message: str, decision: Dict, 
                                     observation: Dict, context: ConversationContext) -> str:
        """Generate natural response using LLM"""
        if not self.llm_client:
            return self._fallback_generate(user_message, decision, observation, context)
        
        order_summary = self._format_order_summary(context.current_order)
        
        prompt = f"""Generate a natural response as Tasha (Wingstop cashier).

CUSTOMER SAID: "{user_message}"

DECIDED INTENT: {decision.get('intent')}
MISSING INFO: {decision.get('missing_info', [])}
OBSERVATIONS: {observation.get('results', [])}

CURRENT ORDER:
{order_summary}

CONVERSATION HISTORY:
{context.get_recent_context(5)}

Respond as Tasha (friendly, helpful, concise under 20 words):
TASHA:"""

        try:
            response = self.llm_client.chat.completions.create(
                model=settings.llm_model if hasattr(settings, 'llm_model') else "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Tasha, a friendly Wingstop cashier. Be natural and conversational."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[Agent] LLM generation error: {e}")
            return self._fallback_generate(user_message, decision, observation, context)
    
    def _fallback_generate(self, user_message: str, decision: Dict, 
                          observation: Dict, context: ConversationContext) -> str:
        """Fallback response generation - natural, no states"""
        intent = decision.get("intent")
        missing = decision.get("missing_info", [])
        order = context.current_order
        items = order.get("items", [])
        
        # Add item needs flavor
        if intent == "add_item_needs_flavor":
            last_item = items[-1] if items else {"name": "wings"}
            return f"Got {last_item.get('quantity', 10)} {last_item.get('name', 'wings')}. What flavor?"
        
        # Add item success
        if intent == "add_item":
            if items:
                last_item = items[-1]
                name = last_item.get('name', 'item')
                flavor = last_item.get('flavor')
                if flavor:
                    return f"Got it! {last_item.get('quantity', 10)} {name} with {flavor}. What else?"
                return f"Got it! Added {last_item.get('quantity', 10)} {name}. What else?"
            return "What would you like to add?"
        
        # Modify item (flavor added)
        if intent == "modify_item":
            if items:
                last_item = items[-1]
                return f"Perfect! {last_item.get('flavor', '')} {last_item.get('name', 'wings')}. Anything else?"
            return "What else would you like?"
        
        # Done ordering - show summary
        if intent == "done_ordering":
            total = sum(item.get("total", 0) for item in items)
            if missing and "customer_name" in missing:
                return f"Your total is ${total:.2f}. What name for the order?"
            return f"Ready to confirm? Your total is ${total:.2f}."
        
        # Confirm
        if intent == "confirm":
            if order.get("customer_name"):
                return f"Order confirmed! Thanks {order['customer_name']}!"
            return "What name should I put this under?"
        
        # Provide info (name given)
        if intent == "provide_info":
            if order.get("customer_name"):
                total = sum(item.get("total", 0) for item in items)
                return f"Thanks {order['customer_name']}! Total is ${total:.2f}. Confirm?"
            return "Got it! What else can I get you?"
        
        # General chat
        if not items:
            return "Welcome to Wingstop! I'm Tasha. What can I get for you?"
        
        return "What else would you like?"
    
    def _parse_items_from_message(self, message: str) -> List[Dict]:
        """Extract items from natural language"""
        items = []
        msg_lower = message.lower()
        
        # Simple parsing - in production use LLM for this
        import re
        
        # Match wing orders
        wing_match = re.search(r'(\d+)?\s*(?:pc|piece)?\s*(boneless|bone-in)?\s*wing', msg_lower)
        if wing_match:
            qty = int(wing_match.group(1)) if wing_match.group(1) else 10
            wing_type = wing_match.group(2) if wing_match.group(2) else 'bone-in'
            
            # Check for flavor
            flavors = ['lemon pepper', 'garlic parmesan', 'original hot', 'bbq', 'mango habanero']
            flavor = None
            for f in flavors:
                if f in msg_lower:
                    flavor = f.title()
                    break
            
            items.append({
                "name": f"{wing_type.title()} Wings",
                "quantity": qty,
                "flavor": flavor,
                "unit_price": 1.19 if wing_type == 'boneless' else 1.29,
                "total": qty * (1.19 if wing_type == 'boneless' else 1.29)
            })
        
        return items
    
    def _extract_name(self, message: str) -> Optional[str]:
        """Extract customer name from message"""
        import re
        patterns = [
            r'name is (\w+)',
            r'for (\w+)$',
            r'^(\w+) here',
            r'^it\'?s (\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1).title()
        return None
    
    def _format_order_summary(self, order: Dict) -> str:
        """Format order for display"""
        if not order.get("items"):
            return "Empty order"
        
        lines = []
        for item in order["items"]:
            line = f"- {item.get('quantity')}x {item.get('name')}"
            if item.get('flavor'):
                line += f" ({item.get('flavor')})"
            lines.append(line)
        
        total = sum(item.get("total", 0) for item in order["items"])
        lines.append(f"Total: ${total:.2f}")
        
        return "\n".join(lines)
    
    def get_order_status(self, session_id: str) -> Dict:
        """Get current order status"""
        context = self.contexts.get(session_id)
        if not context:
            return {"has_order": False}
        
        order = context.current_order
        return {
            "has_order": bool(order.get("items")),
            "item_count": len(order.get("items", [])),
            "total": sum(item.get("total", 0) for item in order.get("items", [])),
            "customer": order.get("customer_name"),
            "items": order.get("items", [])
        }
