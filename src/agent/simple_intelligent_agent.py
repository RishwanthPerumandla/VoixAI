"""
Simple Intelligent Agent - No State Machine, Pure LLM Reasoning
Works reliably without complex tool chains
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.config import settings


@dataclass
class OrderItem:
    name: str
    quantity: int
    flavor: Optional[str] = None
    unit_price: float = 1.29
    
    @property
    def total(self) -> float:
        return self.quantity * self.unit_price
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "flavor": self.flavor,
            "unit_price": self.unit_price,
            "total": self.total
        }


@dataclass
class ConversationMemory:
    """Simple memory - just tracks conversation, not state"""
    messages: List[Dict] = field(default_factory=list)
    items: List[OrderItem] = field(default_factory=list)
    customer_name: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_context(self, n: int = 8) -> str:
        recent = self.messages[-n:] if len(self.messages) > n else self.messages
        lines = []
        for msg in recent:
            role = "Customer" if msg["role"] == "user" else "Tasha"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
    
    @property
    def order_total(self) -> float:
        return sum(item.total for item in self.items)
    
    def get_order_summary(self) -> str:
        if not self.items:
            return "No items yet"
        lines = []
        for item in self.items:
            line = f"- {item.quantity}x {item.name}"
            if item.flavor:
                line += f" ({item.flavor})"
            lines.append(line)
        lines.append(f"Total: ${self.order_total:.2f}")
        return "\n".join(lines)


class SimpleIntelligentAgent:
    """
    Intelligent agent that uses LLM for natural conversation
    but handles order tracking internally without state machines
    """
    
    def __init__(self):
        self.memories: Dict[str, ConversationMemory] = {}
        self.llm_client = None
        if settings.groq_api_key:
            from groq import Groq
            self.llm_client = Groq(api_key=settings.groq_api_key)
    
    def _get_memory(self, session_id: str) -> ConversationMemory:
        if session_id not in self.memories:
            self.memories[session_id] = ConversationMemory()
        return self.memories[session_id]
    
    def _parse_items(self, message: str) -> List[OrderItem]:
        """Parse items from natural language"""
        import re
        msg_lower = message.lower()
        items = []
        
        # Match wing orders
        wing_match = re.search(r'(\d+)?\s*(?:pc|piece)?\s*(boneless|bone-in)?\s*wing', msg_lower)
        if wing_match:
            qty = int(wing_match.group(1)) if wing_match.group(1) else 10
            wing_type = wing_match.group(2) if wing_match.group(2) else 'bone-in'
            name = f"{wing_type.title()} Wings"
            price = 1.19 if wing_type == 'boneless' else 1.29
            items.append(OrderItem(name=name, quantity=qty, unit_price=price))
        
        return items
    
    def _add_flavor(self, message: str, memory: ConversationMemory) -> bool:
        """Add flavor to last wing item"""
        msg_lower = message.lower()
        flavors = [
            'lemon pepper', 'garlic parmesan', 'original hot', 
            'bbq', 'hickory smoked', 'mango habanero', 'atomic',
            'spicy korean', 'cajun', 'plain'
        ]
        
        for flavor in flavors:
            if flavor in msg_lower:
                # Find last wing item without flavor
                for item in reversed(memory.items):
                    if 'wing' in item.name.lower() and not item.flavor:
                        item.flavor = flavor.title()
                        return True
        return False
    
    def _extract_name(self, message: str) -> Optional[str]:
        """Extract customer name"""
        import re
        patterns = [
            r'name is (\w+)',
            r'for (\w+)$',
            r'^(\w+) here',
            r'^it\'?s (\w+)',
            r'put it under (\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1).title()
        return None
    
    def _is_done(self, message: str) -> bool:
        """Check if customer is done ordering"""
        done_phrases = [
            'nothing', 'that\'s all', 'no more', 'i\'m good', 
            'we\'re good', 'done', 'finished', 'complete', 
            'that\'s it', 'no thanks', 'nope', 'just that'
        ]
        msg_lower = message.lower()
        return any(phrase in msg_lower for phrase in done_phrases)
    
    def _is_confirm(self, message: str) -> bool:
        """Check if customer wants to confirm"""
        confirm_phrases = ['confirm', 'place', 'yes', 'order it', 'that works']
        msg_lower = message.lower()
        return any(phrase in msg_lower for phrase in confirm_phrases)
    
    async def process(self, message: str, session_id: str) -> str:
        """Process message with LLM + internal tracking"""
        memory = self._get_memory(session_id)
        memory.add_message("user", message)
        
        # First: Update order based on message content
        order_updated = False
        update_desc = ""
        
        # Check for items to add
        items = self._parse_items(message)
        if items:
            memory.items.extend(items)
            order_updated = True
            update_desc = f"Added {items[0].quantity}x {items[0].name}"
        
        # Check for flavor
        elif self._add_flavor(message, memory):
            order_updated = True
            update_desc = "Added flavor"
        
        # Check for name
        name = self._extract_name(message)
        if name:
            memory.customer_name = name
            order_updated = True
            update_desc = f"Name: {name}"
        
        # Now: Generate response using LLM with full context
        response = await self._generate_response(
            message, memory, order_updated, update_desc
        )
        
        memory.add_message("assistant", response)
        return response
    
    async def _generate_response(self, message: str, memory: ConversationMemory,
                                  order_updated: bool, update_desc: str) -> str:
        """Generate natural response using LLM"""
        
        # Check for special cases first (fast path)
        msg_lower = message.lower()
        
        # Done ordering - show summary
        if self._is_done(message) and memory.items:
            if not memory.customer_name:
                return f"Your total is ${memory.order_total:.2f}. What name for the order?"
            return f"Thanks {memory.customer_name}! Total is ${memory.order_total:.2f}. Ready to confirm?"
        
        # Confirm order
        if self._is_confirm(message) and memory.items:
            if memory.customer_name:
                return f"Order confirmed! Thanks {memory.customer_name}! Your wings will be ready in 15-20 minutes."
            return "What name should I put this order under?"
        
        # Use LLM for natural conversation
        if self.llm_client:
            return await self._llm_response(message, memory, order_updated, update_desc)
        
        # Fallback responses
        return self._fallback_response(message, memory, order_updated)
    
    async def _llm_response(self, message: str, memory: ConversationMemory,
                           order_updated: bool, update_desc: str) -> str:
        """Use LLM to generate response"""
        
        order_context = memory.get_order_summary() if memory.items else "No items yet"
        
        prompt = f"""You are Tasha, a friendly Wingstop cashier. Respond naturally.

CUSTOMER SAID: "{message}"

ORDER CONTEXT:
{order_context}

CUSTOMER NAME: {memory.customer_name or "Not provided"}

CONVERSATION HISTORY:
{memory.get_context(6)}

INSTRUCTIONS:
- Be friendly and helpful
- If they just added items, acknowledge and ask what else
- If they gave a flavor, confirm it
- If they said name, acknowledge it
- Ask for missing info naturally (flavor, name)
- Keep under 20 words when possible
- Don't mention "states" or "machines"
- Just have natural conversation

Respond as Tasha:"""

        try:
            response = self.llm_client.chat.completions.create(
                model=settings.llm_model if hasattr(settings, 'llm_model') else "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Tasha, a friendly Wingstop cashier. Be natural and conversational."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=80,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[Agent] LLM error: {e}")
            return self._fallback_response(message, memory, order_updated)
    
    def _fallback_response(self, message: str, memory: ConversationMemory, 
                          order_updated: bool) -> str:
        """Fallback when LLM unavailable"""
        msg_lower = message.lower()
        
        # Just added items
        if order_updated and memory.items:
            last_item = memory.items[-1]
            if not last_item.flavor and 'wing' in last_item.name.lower():
                return f"Got {last_item.quantity} {last_item.name}. What flavor?"
            return f"Got {last_item.quantity}x {last_item.name}. What else?"
        
        # No items yet
        if not memory.items:
            return "Welcome to Wingstop! I'm Tasha. What can I get you?"
        
        # Check if last item needs flavor
        for item in reversed(memory.items):
            if 'wing' in item.name.lower() and not item.flavor:
                return f"What flavor for your {item.name}?"
        
        # Has items, check for name
        if not memory.customer_name:
            return f"Your total is ${memory.order_total:.2f}. What name for the order?"
        
        return "What else can I get you?"
    
    def get_order_status(self, session_id: str) -> Dict:
        """Get current order status"""
        memory = self.memories.get(session_id)
        if not memory:
            return {"has_order": False}
        
        return {
            "has_order": bool(memory.items),
            "item_count": len(memory.items),
            "total": memory.order_total,
            "customer": memory.customer_name,
            "items": [item.to_dict() for item in memory.items]
        }
