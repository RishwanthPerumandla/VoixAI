"""
Order-Centric Agent
ReAct agent specialized for order management workflows
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

from src.orders.state_machine import OrderManager, Order, OrderItem, OrderState
from src.tools.registry import ToolRegistry


@dataclass
class OrderIntent:
    """Parsed order intent from customer message"""
    intent_type: str  # add_item, remove_item, modify_item, review, confirm, cancel, query
    items: List[Dict] = None
    modifiers: Dict = None
    customer_info: Dict = None
    query_type: str = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.modifiers is None:
            self.modifiers = {}


class OrderUnderstandingEngine:
    """Extracts order-related intents and entities"""
    
    # Intent patterns
    ADD_PATTERNS = ['add', 'get', 'want', 'order', 'like', 'give me', 'i\'ll have', 'can i get']
    REMOVE_PATTERNS = ['remove', 'delete', 'take off', 'don\'t want', 'cancel the', 'get rid of']
    MODIFY_PATTERNS = ['change', 'switch', 'make it', 'instead', 'replace', 'modify']
    REVIEW_PATTERNS = ['review', 'what do i have', 'what\'s in my order', 'show me', 'check my']
    CONFIRM_PATTERNS = ['confirm', 'place the order', 'that\'s it', 'all set', 'looks good', 'pay', 'i\'m done', 'we\'re good']
    CANCEL_PATTERNS = ['cancel', 'start over', 'clear', 'empty', 'delete everything']
    DONE_PATTERNS = ['nothing', 'that\'s all', 'that is all', 'no more', 'i\'m good', 'we\'re good', 'done', 'finished', 'complete', 'that\'s it', 'that is it', 'no thanks', 'no thank you', 'nope', 'just that']
    
    def __init__(self):
        self.menu_keywords = self._load_menu_keywords()
    
    def _load_menu_keywords(self) -> Dict[str, List[str]]:
        """Load menu item keywords for recognition"""
        return {
            'wings': ['wings', 'wing', 'boneless', 'bone-in', 'classic', 'chicken'],
            'flavors': ['lemon pepper', 'original hot', 'garlic parmesan', 'bbq', 'hickory', 
                       'mango habanero', 'atomic', 'spicy', 'mild', 'hot'],
            'sides': ['fries', 'fry', 'seasoned fries', 'cheese fries', 'veggie sticks', 'celery', 'carrots'],
            'dips': ['ranch', 'blue cheese', 'honey mustard', 'cheese sauce', 'dip'],
            'drinks': ['drink', 'soda', 'coke', 'sprite', 'water', 'pepsi']
        }
    
    def parse(self, message: str, current_order: Order) -> OrderIntent:
        """Parse customer message into order intent"""
        message_lower = message.lower()
        
        # Determine intent type
        intent_type = self._classify_intent(message_lower)
        
        # Extract items if adding/modifying
        items = []
        if intent_type in ['add_item', 'modify_item']:
            items = self._extract_items(message_lower)
        
        # Extract modifiers
        modifiers = self._extract_modifiers(message_lower)
        
        # Extract customer info
        customer_info = self._extract_customer_info(message_lower)
        
        return OrderIntent(
            intent_type=intent_type,
            items=items,
            modifiers=modifiers,
            customer_info=customer_info
        )
    
    def _classify_intent(self, message: str) -> str:
        """Classify the order intent"""
        for pattern in self.REMOVE_PATTERNS:
            if pattern in message:
                return 'remove_item'
        
        for pattern in self.MODIFY_PATTERNS:
            if pattern in message:
                return 'modify_item'
        
        for pattern in self.REVIEW_PATTERNS:
            if pattern in message:
                return 'review'
        
        # Check for "done" phrases - if order has items, go to review
        for pattern in self.DONE_PATTERNS:
            if pattern in message:
                return 'review'  # Will show order summary
        
        for pattern in self.CONFIRM_PATTERNS:
            if pattern in message:
                return 'confirm'
        
        for pattern in self.CANCEL_PATTERNS:
            if pattern in message:
                return 'cancel'
        
        for pattern in self.ADD_PATTERNS:
            if pattern in message:
                return 'add_item'
        
        # Default to add_item if menu items mentioned
        if any(keyword in message for keywords in self.menu_keywords.values() for keyword in keywords):
            return 'add_item'
        
        return 'query'
    
    def _extract_items(self, message: str) -> List[Dict]:
        """Extract menu items from message"""
        items = []
        
        # Wing patterns
        import re
        
        # Match quantity + wing type
        wing_pattern = r'(\d+)\s*(?:pc|piece)?\s*(?:boneless|bone-in)?\s*(?:wing)?s?'
        wing_matches = re.findall(wing_pattern, message)
        
        for match in wing_matches:
            qty = int(match) if match else 10
            wing_type = 'boneless' if 'boneless' in message else 'bone-in'
            
            items.append({
                'name': f'{wing_type.title()} Wings',
                'category': 'wings',
                'quantity': qty,
                'wing_type': wing_type
            })
        
        # Check for flavors
        for flavor in self.menu_keywords['flavors']:
            if flavor in message:
                for item in items:
                    item['flavor'] = flavor.title()
                break
        
        return items
    
    def _extract_modifiers(self, message: str) -> Dict:
        """Extract order modifiers"""
        modifiers = {}
        
        if any(w in message for w in ['pickup', 'to go', 'takeout']):
            modifiers['order_type'] = 'pickup'
        elif any(w in message for w in ['delivery', 'deliver']):
            modifiers['order_type'] = 'delivery'
        
        # Extract dips
        for dip in self.menu_keywords['dips']:
            if dip in message:
                modifiers['dips'] = modifiers.get('dips', []) + [dip]
        
        return modifiers
    
    def _extract_customer_info(self, message: str) -> Dict:
        """Extract customer information"""
        info = {}
        
        # Name patterns
        name_patterns = [
            r'name is (\w+)',
            r'it is (\w+) for',
            r'for (\w+)$',
            r'^it\'?s (\w+)',
        ]
        
        import re
        for pattern in name_patterns:
            match = re.search(pattern, message)
            if match:
                info['name'] = match.group(1).title()
                break
        
        # Phone pattern
        phone_pattern = r'(\d{3}[-.]?\d{3}[-.]?\d{4})'
        phone_match = re.search(phone_pattern, message)
        if phone_match:
            info['phone'] = phone_match.group(1)
        
        return info


class OrderReasoningEngine:
    """Reasoning about order actions"""
    
    def __init__(self):
        self.order_manager = OrderManager()
    
    def decide_action(self, intent: OrderIntent, order: Order) -> Dict:
        """Decide what action to take based on intent and order state"""
        
        action_plan = {
            'action': None,
            'params': {},
            'response_required': True,
            'clarification_needed': False
        }
        
        if intent.intent_type == 'add_item':
            if not intent.items:
                action_plan['clarification_needed'] = True
                action_plan['clarification_prompt'] = "What would you like to add?"
            else:
                action_plan['action'] = 'add_items'
                action_plan['params'] = {'items': intent.items}
        
        elif intent.intent_type == 'remove_item':
            action_plan['action'] = 'remove_item'
            if order.is_empty:
                action_plan['response'] = "Your order is empty, so there's nothing to remove."
                action_plan['action'] = None
        
        elif intent.intent_type == 'modify_item':
            if order.is_empty:
                action_plan['response'] = "Your order is empty. What would you like to add?"
                action_plan['action'] = None
            else:
                action_plan['action'] = 'modify_item'
                action_plan['params'] = {'modifiers': intent.modifiers}
        
        elif intent.intent_type == 'review':
            action_plan['action'] = 'show_order'
            action_plan['params'] = {'include_pricing': True}
        
        elif intent.intent_type == 'confirm':
            if order.is_empty:
                action_plan['response'] = "Your order is empty. What would you like to order?"
                action_plan['action'] = None
            elif not order.customer_name:
                action_plan['action'] = 'request_customer_info'
            else:
                action_plan['action'] = 'confirm_order'
        
        elif intent.intent_type == 'cancel':
            action_plan['action'] = 'cancel_order'
        
        # Update customer info if provided
        if intent.customer_info:
            action_plan['update_customer'] = intent.customer_info
        
        return action_plan
    
    def get_missing_requirements(self, order: Order) -> List[str]:
        """Get list of missing order requirements"""
        missing = []
        
        if order.is_empty:
            missing.append('items')
        
        for item in order.items:
            if item.category == 'wings' and not item.flavor:
                missing.append(f'flavor for {item.name}')
        
        if not order.customer_name:
            missing.append('customer name')
        
        return missing


class OrderResponseGenerator:
    """Generate order-focused responses"""
    
    def __init__(self):
        self.templates = {
            'item_added': [
                "Got it! Added {item} to your order.",
                "Added {item}. What else?",
                "You got it! {item} added.",
            ],
            'item_removed': [
                "Removed {item}.",
                "Got it, removed {item} from your order.",
            ],
            'order_summary': [
                "Here's your order:\n{summary}",
                "So far you have:\n{summary}",
            ],
            'confirm_prompt': [
                "Ready to confirm? Your total is ${total}.",
                "Should I place this order for ${total}?",
                "All set? Your order total is ${total}.",
            ],
            'missing_info': [
                "I need a few more details: {missing}",
                "Before I confirm, I need: {missing}",
            ],
            'order_confirmed': [
                "Perfect! Your order #{order_id} is confirmed. Total: ${total}.",
                "Order confirmed! It'll be ready in about 15-20 minutes.",
            ],
            'empty_order': [
                "Your order is empty. What can I get you?",
                "What would you like to order?",
            ],
            'ask_flavor': [
                "What flavor for your {item}?",
                "Which flavor would you like for the {item}?",
            ],
            'ask_name': [
                "What's the name for the order?",
                "Can I get a name for this order?",
            ]
        }
    
    def generate(self, template_key: str, **kwargs) -> str:
        """Generate response from template"""
        import random
        templates = self.templates.get(template_key, ["I'm not sure how to respond."])
        template = random.choice(templates)
        return template.format(**kwargs)
    
    def generate_order_summary(self, order: Order) -> str:
        """Generate natural language order summary"""
        if order.is_empty:
            return self.generate('empty_order')
        
        lines = ["So far you have:"]
        
        for item in order.items:
            line = f"- {item.quantity}x {item.name}"
            if item.flavor:
                line += f" ({item.flavor})"
            lines.append(line)
        
        lines.extend([
            "",
            f"Subtotal: ${order.subtotal:.2f}",
            f"Total: ${order.total:.2f}"
        ])
        
        return "\n".join(lines)


class OrderCentricAgent:
    """
    Order-centric ReAct agent
    Focuses on order management workflows
    """
    
    def __init__(self):
        self.order_manager = OrderManager()
        self.understanding = OrderUnderstandingEngine()
        self.reasoning = OrderReasoningEngine()
        self.response_gen = OrderResponseGenerator()
        self.tools = ToolRegistry().create_default_registry()
    
    async def process(self, user_message: str, session_id: str) -> str:
        """Process user message in order context"""
        
        # Get or create order
        order = self.order_manager.get_or_create_order(session_id)
        
        # Step 1: UNDERSTAND - Parse intent
        intent = self.understanding.parse(user_message, order)
        print(f"[OrderAgent] Intent: {intent.intent_type}, Items: {len(intent.items)}")
        
        # Step 2: REASON - Decide action
        action_plan = self.reasoning.decide_action(intent, order)
        
        # Step 3: ACT - Execute action
        observation = await self._execute_action(action_plan, order, intent)
        
        # Step 4: GENERATE - Create response
        response = self._generate_response(action_plan, order, observation, intent)
        
        return response
    
    async def _execute_action(self, action_plan: Dict, order: Order, intent: OrderIntent) -> Dict:
        """Execute the planned action"""
        action = action_plan.get('action')
        
        if action == 'add_items':
            return await self._add_items_to_order(order, action_plan['params']['items'])
        
        elif action == 'remove_item':
            return await self._remove_item_from_order(order, intent)
        
        elif action == 'show_order':
            return {'order_summary': order.get_summary()}
        
        elif action == 'confirm_order':
            return await self._confirm_order(order)
        
        elif action == 'cancel_order':
            order.transition_to(OrderState.CANCELLED, "customer request")
            return {'cancelled': True}
        
        # Update customer info if provided
        if action_plan.get('update_customer'):
            info = action_plan['update_customer']
            order.set_customer_info(
                name=info.get('name'),
                phone=info.get('phone')
            )
        
        return {}
    
    async def _add_items_to_order(self, order: Order, items: List[Dict]) -> Dict:
        """Add items to order with pricing"""
        added_items = []
        
        for item_data in items:
            # Default pricing
            unit_price = 1.29
            if item_data.get('wing_type') == 'boneless':
                unit_price = 1.19
            
            item = OrderItem(
                id=f"{item_data['name']}_{len(order.items)}",
                name=item_data['name'],
                category=item_data['category'],
                quantity=item_data['quantity'],
                unit_price=unit_price,
                flavor=item_data.get('flavor'),
                wing_type=item_data.get('wing_type')
            )
            
            order.add_item(item)
            added_items.append(item.name)
        
        return {'added': added_items, 'order': order}
    
    async def _remove_item_from_order(self, order: Order, intent: OrderIntent) -> Dict:
        """Remove item from order"""
        if not order.items:
            return {'error': 'Order is empty'}
        
        # Remove last added item for simplicity
        # In production, use item ID or match by name
        last_item = order.items[-1]
        order.remove_item(last_item.id)
        
        return {'removed': last_item.name}
    
    async def _confirm_order(self, order: Order) -> Dict:
        """Confirm and persist order"""
        # Validate order
        missing = self.reasoning.get_missing_requirements(order)
        
        if missing:
            return {'missing': missing, 'can_confirm': False}
        
        # Transition state
        order.transition_to(OrderState.CONFIRMED, "customer confirmed")
        
        # Persist to database (via tools)
        create_tool = self.tools.get('create_order')
        result = await create_tool.execute(
            order_id=order.id,
            items=[item.to_dict() for item in order.items],
            total=order.total,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone
        )
        
        return {'confirmed': True, 'order_id': order.id, 'result': result}
    
    def _generate_response(self, action_plan: Dict, order: Order, 
                          observation: Dict, intent: OrderIntent) -> str:
        """Generate appropriate response"""
        
        # Handle clarification needed
        if action_plan.get('clarification_needed'):
            return action_plan['clarification_prompt']
        
        # Handle pre-defined responses
        if 'response' in action_plan:
            return action_plan['response']
        
        # Generate based on observation
        if 'added' in observation:
            item_names = ', '.join(observation['added'])
            response = self.response_gen.generate('item_added', item=item_names)
            
            # Add follow-up prompt for missing info
            missing = self.reasoning.get_missing_requirements(order)
            if 'flavor' in ' '.join(missing):
                response += " " + self.response_gen.generate('ask_flavor', item=observation['added'][0])
            
            return response
        
        if 'removed' in observation:
            return self.response_gen.generate('item_removed', item=observation['removed'])
        
        if 'order_summary' in observation:
            return observation['order_summary']
        
        if 'confirmed' in observation:
            if observation.get('can_confirm', True):
                return self.response_gen.generate(
                    'order_confirmed',
                    order_id=order.id[:8],
                    total=f"{order.total:.2f}"
                )
            else:
                missing_str = ', '.join(observation['missing'])
                return self.response_gen.generate('missing_info', missing=missing_str)
        
        if 'cancelled' in observation:
            return "Order cancelled. What would you like to order instead?"
        
        # Default response
        if order.is_empty:
            return self.response_gen.generate('empty_order')
        
        return self.response_gen.generate_order_summary(order)
    
    def get_order_status(self, session_id: str) -> Dict:
        """Get current order status for session"""
        order = self.order_manager.get_order(session_id)
        if not order:
            return {'state': 'none', 'items': 0}
        
        return {
            'state': order.state.value,
            'items': order.item_count,
            'total': order.total,
            'can_confirm': not bool(self.reasoning.get_missing_requirements(order))
        }
