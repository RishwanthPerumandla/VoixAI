"""
Tool registry for managing and executing tools
"""

from typing import Dict, Type, Any
from src.tools.base import BaseTool, ToolResult


class ToolRegistry:
    """Registry for all available tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool instance"""
        self._tools[tool.name] = tool
    
    def register_tool_class(self, tool_class: Type[BaseTool]):
        """Register a tool by its class"""
        tool = tool_class()
        self.register(tool)
    
    def get(self, name: str) -> BaseTool:
        """Get a tool by name"""
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]
    
    def list_tools(self) -> list:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def get_all_schemas(self) -> list:
        """Get schemas for all registered tools"""
        return [tool.get_schema() for tool in self._tools.values()]
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with parameters"""
        try:
            tool = self.get(tool_name)
            
            # Circuit breaker check
            if tool.is_circuit_open():
                return ToolResult(
                    success=False,
                    error="Service temporarily unavailable (circuit open)"
                )
            
            # Execute tool
            result = await tool.execute(**params)
            
            # Record result
            if result.success:
                tool.record_success()
            else:
                tool.record_failure()
            
            return result
            
        except KeyError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Execution error: {str(e)}")
    
    def create_default_registry(self):
        """Create registry with all 8 tools for Phase 2"""
        # Import all tools
        from src.tools.menu_search import MenuSearchTool
        from src.tools.order_creation import OrderCreationTool
        from src.tools.price_calculator import PriceCalculatorTool
        from src.tools.order_modification import OrderModificationTool
        from src.tools.upsell_engine import UpsellEngineTool
        from src.tools.policy_checker import PolicyCheckerTool
        from src.tools.ticket_creator import TicketCreatorTool
        
        # Register all tools
        self.register(MenuSearchTool())
        self.register(OrderCreationTool())
        self.register(PriceCalculatorTool())
        self.register(OrderModificationTool())
        self.register(UpsellEngineTool())
        self.register(PolicyCheckerTool())
        self.register(TicketCreatorTool())
        
        print(f"[ToolRegistry] Registered {len(self._tools)} tools: {self.list_tools()}")
        
        return self
