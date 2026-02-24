"""Tool definitions for the ReAct agent - Business logic functions"""
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MenuItem:
    """Represents a menu item"""
    name: str
    category: str
    description: str
    prices: Dict[str, float]  # size -> price mapping
    heat_level: int = 0  # 0-4 scale
    popular: bool = False
    available: bool = True
    tags: List[str] = field(default_factory=list)
    calories: Optional[int] = None


@dataclass
class OrderLineItem:
    """Represents an item in an order"""
    item_name: str
    quantity: int
    size: str = ""
    modifiers: Dict[str, Any] = field(default_factory=dict)
    unit_price: float = 0.0
    
    @property
    def total_price(self) -> float:
        return self.unit_price * self.quantity


class MenuManager:
    """Manages menu data and search"""
    
    def __init__(self, menu_path: str = "data/menu.json"):
        self.menu_path = menu_path
        self.items: List[MenuItem] = []
        self._load_menu()
    
    def _load_menu(self):
        """Load menu from JSON or create default"""
        try:
            with open(self.menu_path, 'r') as f:
                data = json.load(f)
                for item_data in data.get('items', []):
                    self.items.append(MenuItem(**item_data))
        except FileNotFoundError:
            self._create_default_menu()
    
    def _create_default_menu(self):
        """Create default Wingstop menu"""
        self.items = [
            # Wings - Boneless
            MenuItem("Boneless Wings", "wings", "Crispy boneless chicken wings", 
                    {"6pc": 10.99, "8pc": 13.99, "10pc": 16.99, "15pc": 23.99, "20pc": 29.99, "30pc": 42.99},
                    heat_level=0, popular=True, tags=["boneless", "crispy"]),
            # Wings - Bone-in
            MenuItem("Bone-In Wings", "wings", "Classic bone-in wings",
                    {"6pc": 9.99, "8pc": 12.99, "10pc": 15.99, "15pc": 21.99, "20pc": 27.99, "30pc": 39.99},
                    heat_level=0, popular=True, tags=["bone-in", "classic"]),
            
            # Flavors (as modifiers but listed for search)
            MenuItem("Lemon Pepper", "flavor", "Tangy lemon with black pepper - our #1 seller",
                    {"addon": 0}, heat_level=0, popular=True, tags=["citrus", "mild", "bestseller"]),
            MenuItem("Garlic Parmesan", "flavor", "Savory garlic with parmesan",
                    {"addon": 0}, heat_level=0, tags=["savory", "mild"]),
            MenuItem("Cajun", "flavor", "Louisiana-style seasoning",
                    {"addon": 0}, heat_level=1, tags=["spicy", "seasoned"]),
            MenuItem("Hickory Smoked BBQ", "flavor", "Sweet and smoky barbecue",
                    {"addon": 0}, heat_level=0, tags=["sweet", "smoky"]),
            MenuItem("Mild", "flavor", "Classic mild buffalo",
                    {"addon": 0}, heat_level=1, tags=["buffalo", "classic"]),
            MenuItem("Original Hot", "flavor", "Traditional hot wing sauce",
                    {"addon": 0}, heat_level=2, popular=True, tags=["hot", "classic", "vinegar"]),
            MenuItem("Mango Habanero", "flavor", "Sweet mango with habanero kick",
                    {"addon": 0}, heat_level=3, tags=["sweet", "hot", "fruity"]),
            MenuItem("Atomic", "flavor", "Nuclear heat - our hottest",
                    {"addon": 0}, heat_level=4, tags=["extreme", "spicy", "challenge"]),
            MenuItem("Korean BBQ", "flavor", "Sweet and savory Korean style",
                    {"addon": 0}, heat_level=1, tags=["sweet", "savory", "asian"]),
            MenuItem("Spicy Korean", "flavor", "Hot Korean chili",
                    {"addon": 0}, heat_level=3, tags=["spicy", "asian"]),
            MenuItem("Louisiana Rub", "flavor", "Dry rub with Cajun spices",
                    {"addon": 0}, heat_level=1, tags=["dry", "seasoned", "rub"]),
            
            # Sides
            MenuItem("Seasoned Fries", "sides", "Our famous seasoned fries",
                    {"regular": 3.99, "large": 5.49}, popular=True, tags=["classic"]),
            MenuItem("Veggie Sticks", "sides", "Fresh celery and carrots",
                    {"regular": 3.99}, tags=["healthy", "fresh"]),
            MenuItem("Cheese Fries", "sides", "Fries with cheese sauce",
                    {"regular": 5.49, "large": 6.99}, tags=["cheese"]),
            MenuItem("Buffalo Ranch Fries", "sides", "Fries with buffalo and ranch",
                    {"regular": 5.49}, heat_level=2, tags=["spicy"]),
            MenuItem("Cajun Corn", "sides", "Corn on the cob with Cajun seasoning",
                    {"regular": 3.49}, tags=["corn"]),
            MenuItem("Coleslaw", "sides", "Creamy coleslaw",
                    {"regular": 2.99}, tags=["fresh"]),
            
            # Drinks
            MenuItem("Coke", "drinks", "Coca-Cola",
                    {"20oz": 2.49, "32oz": 3.49}, tags=["soda"]),
            MenuItem("Diet Coke", "drinks", "Diet Coca-Cola",
                    {"20oz": 2.49, "32oz": 3.49}, tags=["soda", "diet"]),
            MenuItem("Sprite", "drinks", "Lemon-lime soda",
                    {"20oz": 2.49, "32oz": 3.49}, tags=["soda"]),
            MenuItem("Dr Pepper", "drinks", "Dr Pepper",
                    {"20oz": 2.49, "32oz": 3.49}, tags=["soda"]),
            MenuItem("Lemonade", "drinks", "Fresh-squeezed lemonade",
                    {"20oz": 2.99, "32oz": 3.99}, popular=True, tags=["fresh"]),
            MenuItem("Strawberry Lemonade", "drinks", "Lemonade with strawberry",
                    {"20oz": 3.49, "32oz": 4.49}, tags=["fresh", "fruity"]),
            MenuItem("Iced Tea", "drinks", "Fresh brewed iced tea",
                    {"20oz": 2.49, "32oz": 3.49}, tags=["tea"]),
            MenuItem("Sweet Tea", "drinks", "Southern sweet tea",
                    {"20oz": 2.49, "32oz": 3.49}, popular=True, tags=["tea", "sweet"]),
            
            # Dips
            MenuItem("Ranch", "dips", "Classic ranch dressing",
                    {"regular": 0.99}, popular=True),
            MenuItem("Blue Cheese", "dips", "Creamy blue cheese",
                    {"regular": 0.99}),
            MenuItem("Honey Mustard", "dips", "Sweet honey mustard",
                    {"regular": 0.99}),
            MenuItem("Cheese Sauce", "dips", "Nacho cheese",
                    {"regular": 0.99}),
            
            # Combos
            MenuItem("6pc Combo", "combos", "6 wings + fries + drink (saves $3)",
                    {"combo": 13.99}, tags=["combo", "value"]),
            MenuItem("8pc Combo", "combos", "8 wings + fries + drink (saves $3)",
                    {"combo": 16.99}, tags=["combo", "value"]),
            MenuItem("10pc Combo", "combos", "10 wings + fries + drink (saves $3)",
                    {"combo": 19.99}, popular=True, tags=["combo", "value"]),
            MenuItem("15pc Combo", "combos", "15 wings + fries + drink (saves $6.50)",
                    {"combo": 23.99}, tags=["combo", "value"]),
        ]
        self._save_menu()
    
    def _save_menu(self):
        """Save menu to JSON"""
        import os
        os.makedirs("data", exist_ok=True)
        data = {
            "items": [
                {
                    "name": item.name,
                    "category": item.category,
                    "description": item.description,
                    "prices": item.prices,
                    "heat_level": item.heat_level,
                    "popular": item.popular,
                    "available": item.available,
                    "tags": item.tags,
                    "calories": item.calories
                }
                for item in self.items
            ]
        }
        with open(self.menu_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def search(self, query: str = "", category: str = "", 
               max_price: float = None, limit: int = 5) -> List[Dict]:
        """Search menu items"""
        query_lower = query.lower()
        results = []
        
        for item in self.items:
            if not item.available:
                continue
                
            # Category filter
            if category and item.category != category:
                continue
            
            # Price filter
            if max_price:
                min_item_price = min(item.prices.values()) if item.prices else 0
                if min_item_price > max_price:
                    continue
            
            # Text search (match name, description, or tags)
            if query:
                match_score = 0
                if query_lower in item.name.lower():
                    match_score += 10
                if query_lower in item.description.lower():
                    match_score += 5
                for tag in item.tags:
                    if query_lower in tag.lower():
                        match_score += 3
                
                if match_score == 0:
                    continue
            
            results.append({
                "name": item.name,
                "category": item.category,
                "description": item.description,
                "prices": item.prices,
                "heat_level": item.heat_level,
                "popular": item.popular,
                "tags": item.tags
            })
        
        # Sort by popularity and limit
        results.sort(key=lambda x: (not x["popular"], x["name"]))
        return results[:limit]
    
    def get_item(self, name: str) -> Optional[MenuItem]:
        """Get specific item by name"""
        name_lower = name.lower()
        # Fuzzy matching
        for item in self.items:
            if name_lower in item.name.lower() or item.name.lower() in name_lower:
                return item
        return None
    
    def get_flavors(self, heat_max: int = 4) -> List[Dict]:
        """Get available flavors filtered by heat"""
        flavors = []
        for item in self.items:
            if item.category == "flavor" and item.heat_level <= heat_max:
                flavors.append({
                    "name": item.name,
                    "heat_level": item.heat_level,
                    "description": item.description,
                    "popular": item.popular
                })
        return sorted(flavors, key=lambda x: (not x["popular"], x["heat_level"]))


class PricingEngine:
    """Handles price calculations"""
    
    TAX_RATE = 0.08
    COMBO_DISCOUNTS = {
        6: 3.00,
        8: 3.00,
        10: 3.00,
        15: 6.50,
        20: 8.00,
        30: 10.00
    }
    
    def calculate(self, items: List[OrderLineItem], 
                  apply_combo_discounts: bool = True) -> Dict[str, Any]:
        """Calculate total with tax and discounts"""
        subtotal = 0.0
        breakdown = []
        
        for item in items:
            item_total = item.total_price
            subtotal += item_total
            breakdown.append({
                "item": item.item_name,
                "qty": item.quantity,
                "unit_price": item.unit_price,
                "total": item_total
            })
        
        # Apply combo discount if applicable
        savings = 0.0
        if apply_combo_discounts:
            wing_qty = sum(item.quantity for item in items 
                          if "wing" in item.item_name.lower())
            if wing_qty >= 6:
                # Find applicable discount
                for qty in sorted(self.COMBO_DISCOUNTS.keys(), reverse=True):
                    if wing_qty >= qty:
                        savings = self.COMBO_DISCOUNTS[qty]
                        break
        
        discounted_subtotal = max(0, subtotal - savings)
        tax = discounted_subtotal * self.TAX_RATE
        total = discounted_subtotal + tax
        
        return {
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(total, 2),
            "savings": round(savings, 2),
            "breakdown": breakdown
        }


class TicketManager:
    """Manages support tickets"""
    
    def __init__(self):
        self.tickets: List[Dict] = []
        self._counter = 5600
    
    def create(self, ticket_type: str, description: str, 
               order_id: str = None, severity: str = "medium") -> Dict:
        """Create a new support ticket"""
        self._counter += 1
        ticket = {
            "ticket_id": f"TKT-{self._counter}",
            "type": ticket_type,
            "description": description,
            "order_id": order_id,
            "severity": severity,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "estimated_response": "15 minutes" if severity == "high" else "30 minutes"
        }
        self.tickets.append(ticket)
        return ticket
    
    def get_status(self, ticket_id: str) -> Optional[Dict]:
        """Get ticket status"""
        for ticket in self.tickets:
            if ticket["ticket_id"] == ticket_id:
                return ticket
        return None


# Tool functions for ReAct agent

def search_menu(query: str = "", category: str = "", 
                max_price: float = None, limit: int = 5,
                menu_manager: MenuManager = None) -> Dict[str, Any]:
    """Find menu items matching criteria"""
    if menu_manager is None:
        menu_manager = MenuManager()
    
    results = menu_manager.search(query, category, max_price, limit)
    return {
        "results": results,
        "count": len(results),
        "query": query
    }


def calculate_price(items: List[Dict], apply_combo_discounts: bool = True) -> Dict[str, Any]:
    """Calculate total with tax, discounts, combos"""
    pricing = PricingEngine()
    
    # Convert dict items to OrderLineItem
    line_items = []
    for item in items:
        line_item = OrderLineItem(
            item_name=item.get("name", "Unknown"),
            quantity=item.get("qty", 1),
            size=item.get("size", ""),
            unit_price=item.get("unit_price", 0.0),
            modifiers=item.get("modifiers", {})
        )
        line_items.append(line_item)
    
    return pricing.calculate(line_items, apply_combo_discounts)


def validate_order(items: List[Dict]) -> Dict[str, Any]:
    """Validate order for completeness and constraints"""
    errors = []
    warnings = []
    
    if not items:
        errors.append("Order is empty")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # Check for wings without flavors
    for item in items:
        if "wing" in item.get("name", "").lower():
            mods = item.get("modifiers", {})
            flavors = mods.get("flavors", [])
            if not flavors:
                errors.append(f"Wings need at least one flavor")
            
            # Check flavor qty matches wing qty
            total_flavor_qty = sum(f.get("qty", 0) for f in flavors)
            if total_flavor_qty != item.get("qty", 0):
                warnings.append(f"Flavor quantities don't match wing count")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def suggest_upsell(current_items: List[Dict], 
                   conversation_stage: str = "mid") -> Dict[str, Any]:
    """Generate personalized upsell suggestion"""
    
    has_wings = any("wing" in item.get("name", "").lower() for item in current_items)
    has_drink = any(item.get("category") == "drinks" for item in current_items)
    has_side = any(item.get("category") == "sides" for item in current_items)
    has_combo = any(item.get("category") == "combos" for item in current_items)
    
    # Determine best upsell
    if has_wings and not has_combo and not (has_drink and has_side):
        # Suggest combo upgrade
        wing_qty = 0
        for item in current_items:
            if "wing" in item.get("name", "").lower():
                wing_qty = item.get("qty", 0)
                break
        
        if wing_qty >= 6:
            return {
                "type": "combo",
                "suggestion": f"Make it a {wing_qty}pc combo? Gets you fries and a drink.",
                "value_proposition": f"Saves ${3.00 if wing_qty <= 10 else 6.50:.2f}",
                "target_price": 19.99 if wing_qty == 10 else 23.99
            }
    
    if has_wings and has_drink and not has_side:
        return {
            "type": "side",
            "suggestion": "Add seasoned fries? They're fresh-cut daily.",
            "value_proposition": "Only $3.99",
            "target_price": 3.99
        }
    
    if has_wings and not has_drink:
        return {
            "type": "drink",
            "suggestion": "Our lemonade is fresh-squeezed if you want a drink",
            "value_proposition": "$2.99 for 20oz",
            "target_price": 2.99
        }
    
    return {
        "type": "none",
        "suggestion": "",
        "value_proposition": "",
        "target_price": 0
    }


def create_ticket(ticket_type: str, description: str, 
                  order_id: str = None, severity: str = "medium",
                  ticket_manager: TicketManager = None) -> Dict[str, Any]:
    """Create support ticket for issues"""
    if ticket_manager is None:
        ticket_manager = TicketManager()
    
    return ticket_manager.create(ticket_type, description, order_id, severity)


def escalate_to_human(reason: str, urgency: str = "normal", 
                      context_summary: str = "") -> Dict[str, Any]:
    """Transfer to human agent"""
    queue_position = 2 if urgency == "urgent" else 5
    wait_time = "2-3 minutes" if urgency == "urgent" else "5-7 minutes"
    
    return {
        "queue_position": queue_position,
        "estimated_wait": wait_time,
        "handoff_success": True,
        "reason": reason,
        "context": context_summary
    }


def get_order_status(order_id: str) -> Dict[str, Any]:
    """Get order status (placeholder - would query DB)"""
    return {
        "order_id": order_id,
        "status": "preparing",  # building|confirmed|preparing|ready|completed
        "estimated_ready": "15 minutes",
        "progress_percent": 60
    }


# Tool registry for LLM
TOOL_DEFINITIONS = [
    {
        "name": "search_menu",
        "description": "Find menu items matching criteria. Use for menu questions, recommendations, or finding items.",
        "parameters": {
            "query": "Search text like 'spicy wings' or 'bbq'",
            "category": "Filter by: wings, sides, drinks, desserts, combos, flavor",
            "max_price": "Maximum price filter",
            "limit": "Max results to return (default 5)"
        }
    },
    {
        "name": "calculate_price",
        "description": "Calculate order total with tax and discounts. Use when customer asks about pricing or before confirming order.",
        "parameters": {
            "items": "List of items with name, qty, unit_price",
            "apply_combo_discounts": "Whether to apply combo savings (default true)"
        }
    },
    {
        "name": "validate_order",
        "description": "Check if order is complete and valid. Use before finalizing.",
        "parameters": {
            "items": "List of order items to validate"
        }
    },
    {
        "name": "suggest_upsell",
        "description": "Get personalized upsell suggestion based on current order.",
        "parameters": {
            "current_items": "Current order items",
            "conversation_stage": "early|mid|closing"
        }
    },
    {
        "name": "create_ticket",
        "description": "Create support ticket for complaints or issues. Use when customer has problems.",
        "parameters": {
            "ticket_type": "complaint|refund|missing_item|quality_issue",
            "description": "Description of the issue",
            "order_id": "Optional order reference",
            "severity": "low|medium|high"
        }
    },
    {
        "name": "escalate_to_human",
        "description": "Transfer to human agent. Use for angry customers or complex issues.",
        "parameters": {
            "reason": "Why escalation is needed",
            "urgency": "normal|urgent",
            "context_summary": "Brief summary for human agent"
        }
    },
    {
        "name": "get_order_status",
        "description": "Check status of existing order.",
        "parameters": {
            "order_id": "Order ID to check"
        }
    }
]
