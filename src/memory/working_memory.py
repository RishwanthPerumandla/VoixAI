"""
Working Memory - Last 5 turns
Fast, in-memory storage for current conversation context
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


class WorkingMemory:
    """Working memory storing last N conversation turns"""
    
    def __init__(self, capacity: int = 5):
        self.capacity = capacity
        self._turns: deque = deque(maxlen=capacity)
        self._current_order: Optional[Dict] = None
        self._customer_info: Dict = {}
    
    def add_turn(self, role: str, content: str, metadata: Dict = None):
        """Add a conversation turn"""
        turn = ConversationTurn(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._turns.append(turn)
    
    def get_recent(self, n: int = None) -> List[Dict]:
        """Get recent turns as list"""
        n = n or self.capacity
        return [
            {
                "role": turn.role,
                "content": turn.content,
                "timestamp": turn.timestamp.isoformat()
            }
            for turn in list(self._turns)[-n:]
        ]
    
    def get_context_for_prompt(self) -> str:
        """Get formatted conversation history for LLM prompt"""
        turns = self.get_recent()
        formatted = []
        for turn in turns:
            role_label = "Customer" if turn["role"] == "user" else "Assistant"
            formatted.append(f"{role_label}: {turn['content']}")
        return "\n".join(formatted)
    
    def set_current_order(self, order: Dict):
        """Set current order being built"""
        self._current_order = order
    
    def get_current_order(self) -> Optional[Dict]:
        """Get current order"""
        return self._current_order
    
    def set_customer_info(self, info: Dict):
        """Set customer information"""
        self._customer_info.update(info)
    
    def get_customer_info(self) -> Dict:
        """Get customer information"""
        return self._customer_info
    
    def clear(self):
        """Clear working memory"""
        self._turns.clear()
        self._current_order = None
        self._customer_info = {}
    
    def is_empty(self) -> bool:
        """Check if memory is empty"""
        return len(self._turns) == 0
