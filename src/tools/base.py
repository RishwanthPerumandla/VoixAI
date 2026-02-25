"""
Base tool interface for VoixAI v3.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Base class for all tools"""
    
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    
    def __init__(self):
        self._failure_count = 0
        self._success_count = 0
        self._circuit_open = False
    
    @abstractmethod
    async def execute(self, **params) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        return self._circuit_open
    
    def record_success(self):
        """Record a successful execution"""
        self._success_count += 1
        self._failure_count = 0
        self._circuit_open = False
    
    def record_failure(self):
        """Record a failed execution"""
        self._failure_count += 1
        if self._failure_count >= 5:
            self._circuit_open = True
    
    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAI function schema for this tool"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
