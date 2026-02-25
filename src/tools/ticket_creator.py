"""
Ticket Creator Tool
Create support tickets for issues/escalations
"""

from typing import Dict, List, Any
from src.tools.base import BaseTool, ToolResult
import json
from pathlib import Path
from datetime import datetime


class TicketCreatorTool(BaseTool):
    """Create support tickets for issues"""
    
    name = "create_ticket"
    description = "Create a support ticket for complaints, issues, refunds, or special requests that need human attention"
    parameters = {
        "type": "object",
        "properties": {
            "ticket_type": {
                "type": "string",
                "enum": ["complaint", "refund_request", "order_issue", "special_request", "general_inquiry"],
                "description": "Type of ticket"
            },
            "description": {"type": "string", "description": "Detailed description of the issue"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "default": "medium"
            },
            "customer_info": {"type": "object", "description": "Customer information"},
            "order_id": {"type": "string", "description": "Related order ID if applicable"}
        },
        "required": ["ticket_type", "description"]
    }
    
    def __init__(self, db_path: str = "data/tickets.json"):
        super().__init__()
        self.db_path = Path(db_path)
    
    async def execute(
        self,
        ticket_type: str,
        description: str,
        priority: str = "medium",
        customer_info: Dict = None,
        order_id: str = None
    ) -> ToolResult:
        """Create a support ticket"""
        try:
            # Load existing tickets
            tickets = self._load_tickets()
            
            # Generate ticket ID
            ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Create ticket
            ticket = {
                "id": ticket_id,
                "type": ticket_type,
                "description": description,
                "priority": priority,
                "status": "open",
                "customer_info": customer_info or {},
                "order_id": order_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "assigned_to": None,
                "resolution_notes": None
            }
            
            # Auto-assign priority based on type
            if ticket_type == "complaint":
                ticket["priority"] = "high"
            elif ticket_type == "refund_request":
                ticket["priority"] = "medium"
            elif ticket_type == "order_issue":
                ticket["priority"] = "high"
            
            tickets.append(ticket)
            
            # Save tickets
            self._save_tickets(tickets)
            
            # Generate response message
            response_msg = self._generate_response(ticket_type, priority, ticket_id)
            
            return ToolResult(
                success=True,
                data={
                    "ticket_id": ticket_id,
                    "type": ticket_type,
                    "priority": ticket["priority"],
                    "status": "open",
                    "message": response_msg,
                    "estimated_response": "15-30 minutes" if ticket["priority"] in ["high", "urgent"] else "1-2 hours"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=f"Ticket creation failed: {str(e)}")
    
    def _generate_response(self, ticket_type: str, priority: str, ticket_id: str) -> str:
        """Generate appropriate response message"""
        responses = {
            "complaint": f"I'm sorry to hear about your experience. I've created ticket {ticket_id} and our manager will contact you within 15 minutes to make this right.",
            "refund_request": f"I've submitted your refund request as ticket {ticket_id}. Our team will review it and process within 24 hours. You'll receive an email confirmation.",
            "order_issue": f"I've logged your order issue as ticket {ticket_id}. A team member will call you shortly to resolve this.",
            "special_request": f"I've noted your special request as ticket {ticket_id}. We'll do our best to accommodate and will confirm shortly.",
            "general_inquiry": f"I've created ticket {ticket_id} for your inquiry. Someone from our team will get back to you within an hour."
        }
        
        return responses.get(ticket_type, f"Ticket {ticket_id} created. Our team will assist you shortly.")
    
    def _load_tickets(self) -> List[Dict]:
        """Load tickets from file"""
        if not self.db_path.exists():
            return []
        
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def _save_tickets(self, tickets: List[Dict]):
        """Save tickets to file"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w') as f:
            json.dump(tickets, f, indent=2)
