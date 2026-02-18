"""LLM Agent using Groq for fast inference"""
import os
import json
import time
from enum import Enum
from typing import Tuple, Optional, Dict, List, Any
from groq import Groq


class ConversationState(Enum):
    """State machine for conversation flow"""
    GREETING = "greeting"
    TAKING_ITEMS = "taking_items"
    MODIFYING = "modifying"
    CONFIRMING = "confirming"
    CLOSING = "closing"


class ConversationAgent:
    """Tasha - Wingstop Cashier AI with Groq (fast inference)"""
    
    # Tasha's personality - casual, fast, friendly
    def _get_system_prompt(self):
        """Get system prompt with current state context"""
        base_prompt = (
            "You are Tasha, a Wingstop cashier. "
            "Use casual speech: 'lemme', 'gonna', 'gotcha', 'alright', 'yeah'. "
            "Keep responses SHORT (5-12 words max). "
            "Never say 'As an AI', 'I apologize', or formal phrases. "
            "Talk like a real fast-food worker. "
        )
        
        # Add state-specific context
        if self.state == ConversationState.GREETING:
            base_prompt += "You're greeting the customer. Ask what they want to order. Be clear about boneless vs bone-in wings."
        elif self.state == ConversationState.TAKING_ITEMS:
            item_count = sum(item.get("qty", 1) for item in self.order_items)
            if item_count > 0:
                items_str = ", ".join([f"{i.get('qty', 1)} {i.get('name', 'item')}" for i in self.order_items[-3:]])
                base_prompt += f"Current order: {items_str}. Ask if they want anything else or if that's all."
            else:
                base_prompt += "Taking the order. Ask what they want."
        elif self.state == ConversationState.CONFIRMING:
            item_count = sum(item.get("qty", 1) for item in self.order_items)
            items_list = "; ".join([f"{i.get('qty', 1)} {i.get('name')} ({i.get('modifiers', 'no flavor')})" for i in self.order_items])
            base_prompt += f"Confirming order: {items_list}. If they say yes/yeah/sure, say 'Great! Your order is confirmed.' If no, ask what to change."
        elif self.state == ConversationState.CLOSING:
            base_prompt += "Order is complete. Thank them and say goodbye."
        
        return base_prompt
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Groq client with function calling setup"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        # Configure Groq
        self.client = Groq(api_key=api_key)
        
        self.config = config
        self.model_name = config.get("model", "llama-3.3-70b-versatile")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 150)
        
        # Define function schema for order extraction (Groq tool format)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "extract_order_items",
                    "description": "Extract order items from customer speech. Be careful to distinguish 'boneless wings' from 'bone-in wings' or 'classic wings'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "description": "List of food/drink items ordered",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Item name like 'boneless wings', 'bone-in wings', 'Coke', 'fries'"},
                                        "qty": {"type": "integer", "description": "Quantity"},
                                        "modifiers": {"type": "string", "description": "Flavor like 'lemon pepper', 'cajun', 'mild', 'hot'"},
                                        "category": {"type": "string", "enum": ["wings", "side", "drink", "dip"], "description": "Category"}
                                    },
                                    "required": ["name", "qty"]
                                }
                            },
                            "order_complete": {
                                "type": "boolean",
                                "description": "True if customer said that's all/finished ordering"
                            },
                            "special_instructions": {
                                "type": "string",
                                "description": "Any special requests or notes"
                            }
                        },
                        "required": ["items", "order_complete"]
                    }
                }
            }
        ]
        
        # State
        self.state = ConversationState.GREETING
        self.conversation_history: List[Dict] = []
        self.order_items: List[Dict] = []
        self.retry_count = 0
    
    def process(self, user_text: str) -> Tuple[str, Optional[Dict]]:
        """
        Process user input and return Tasha's response + optional order data.
        Returns: (response_text, order_data_dict or None)
        """
        try:
            # Check for simple confirmations/rejections before calling LLM
            user_lower = user_text.lower().strip().rstrip('.!?')
            
            # Handle "repeat order" / "what did I order" queries
            if any(phrase in user_lower for phrase in ["repeat", "what did i order", "what's my order", "what is my order"]):
                print(f"[Agent] Repeat order query detected. Items: {len(self.order_items)}")
                if self.order_items:
                    items_desc = ", ".join([f"{i.get('qty', 1)} {i.get('name', 'item')}" for i in self.order_items])
                    total = sum(item.get("qty", 1) for item in self.order_items)
                    response_text = f"You got {items_desc}. That's {total} items."
                else:
                    response_text = "You haven't ordered anything yet. What can I getcha?"
                self.conversation_history.append({"role": "user", "content": user_text})
                self.conversation_history.append({"role": "assistant", "content": response_text})
                return response_text, {"items": self.order_items, "order_complete": False}
            
            # Handle confirmation responses
            if self.state == ConversationState.CONFIRMING:
                if user_lower in ['yes', 'yeah', 'yep', 'sure', 'yup', 'ok', 'okay']:
                    self.state = ConversationState.CLOSING
                    response_text = "Great! Your order's confirmed. Thanks!"
                    self.conversation_history.append({"role": "user", "content": user_text})
                    self.conversation_history.append({"role": "assistant", "content": response_text})
                    return response_text, {"items": self.order_items, "order_complete": True}
                elif user_lower in ['no', 'nope', 'nah']:
                    self.state = ConversationState.MODIFYING
                    response_text = "No prob, what needs changing?"
                    self.conversation_history.append({"role": "user", "content": user_text})
                    self.conversation_history.append({"role": "assistant", "content": response_text})
                    return response_text, {"items": self.order_items, "order_complete": False}
            
            # Handle completion phrases in TAKING_ITEMS state
            if self.state == ConversationState.TAKING_ITEMS:
                if any(phrase in user_lower for phrase in ["that's all", "that is all", "done", "finished", "complete", "that's it"]):
                    self.state = ConversationState.CONFIRMING
                    total = sum(item.get("qty", 1) for item in self.order_items)
                    response_text = f"That's {total} items total. Look right?"
                    self.conversation_history.append({"role": "user", "content": user_text})
                    self.conversation_history.append({"role": "assistant", "content": response_text})
                    return response_text, {"items": self.order_items, "order_complete": True}
            
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": user_text})
            
            # Keep only last 4 turns (8 messages) to prevent context overload
            if len(self.conversation_history) > 8:
                self.conversation_history = self.conversation_history[-8:]
            
            # Build messages with dynamic system prompt
            system_prompt = self._get_system_prompt()
            messages = [
                {"role": "system", "content": system_prompt}
            ] + self.conversation_history
            
            print(f"[Agent] State: {self.state.value}, Items: {len(self.order_items)}")
            
            # Call Groq API
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=self.tools,
                tool_choice="auto"
            )
            api_time = time.time() - start_time
            print(f"[Agent] Groq API took {api_time:.2f}s")
            
            # Parse response
            message = response.choices[0].message
            response_text = message.content or ""
            order_data = None
            
            # Handle tool calls - need to provide results back to LLM
            if message.tool_calls:
                tool_call = message.tool_calls[0]  # Handle first tool call
                if tool_call.function.name == "extract_order_items":
                    try:
                        order_data = json.loads(tool_call.function.arguments)
                        print(f"[Agent] Tool called with: {order_data}")
                        
                        # Update internal order state
                        if "items" in order_data:
                            self._update_order_items(order_data["items"])
                        # Update state machine
                        self._update_state(order_data)
                        
                        # Add assistant message with tool call to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": message.content or "",
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            }]
                        })
                        
                        # Add tool result message
                        tool_result = {
                            "success": True,
                            "items_added": len(order_data.get("items", [])),
                            "total_items": sum(item.get("qty", 1) for item in self.order_items),
                            "order_complete": order_data.get("order_complete", False)
                        }
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result)
                        })
                        
                        # Call LLM again with tool result to get natural response
                        messages_with_result = [
                            {"role": "system", "content": self._get_system_prompt()}
                        ] + self.conversation_history
                        
                        response2 = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages_with_result,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens
                        )
                        response_text = response2.choices[0].message.content or ""
                        print(f"[Agent] Response after tool: '{response_text[:50]}...'")
                        
                    except json.JSONDecodeError as e:
                        print(f"[Agent] Failed to parse tool arguments: {e}")
                        response_text = "Sorry, say that again?"
            
            # Update state based on user intent if no tool call
            elif not order_data:
                user_lower = user_text.lower()
                if any(x in user_lower for x in ["that's all", "that is all", "done", "finished", "complete"]):
                    order_data = {"items": [], "order_complete": True}
                    self._update_state(order_data)
                elif any(x in user_lower for x in ["yes", "yeah", "yep", "sure"]):
                    if self.state == ConversationState.CONFIRMING:
                        order_data = {"items": [], "order_complete": True}
                        self._update_state(order_data)
            
            # Clean response
            response_text = self._clean_response(response_text)
            
            # If no text response, generate based on state
            if not response_text:
                if order_data and order_data.get("order_complete"):
                    response_text = self._generate_confirmation()
                elif order_data and order_data.get("items"):
                    response_text = self._generate_item_ack(order_data["items"])
                elif self.state == ConversationState.GREETING:
                    response_text = "Hey! What can I getcha?"
                elif self.state == ConversationState.TAKING_ITEMS:
                    response_text = "Gotcha, anything else?"
                elif self.state == ConversationState.CONFIRMING:
                    response_text = "That look right?"
                else:
                    response_text = "Thanks for coming in!"
            
            # Default response if still empty
            if not response_text:
                if self.state == ConversationState.GREETING:
                    response_text = "Hey! What can I getcha?"
                elif self.state == ConversationState.TAKING_ITEMS:
                    response_text = "Gotcha, anything else?"
                elif self.state == ConversationState.CONFIRMING:
                    response_text = "That look right?"
                else:
                    response_text = "Thanks for coming in!"
            
            # Add to history
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            # Retry counter reset on success
            self.retry_count = 0
            
            return response_text, order_data
            
        except Exception as e:
            print(f"[Agent] Error: {e}")
            self.retry_count += 1
            if self.retry_count <= 1:
                # Retry once
                try:
                    return self.process(user_text)
                except Exception as e2:
                    print(f"[Agent] Retry failed: {e2}")
                    pass
            # Fallback response based on state
            if self.state == ConversationState.GREETING:
                return "Hey! What can I getcha?", None
            elif self.state == ConversationState.TAKING_ITEMS:
                return "Gotcha, anything else?", None
            elif self.state == ConversationState.CONFIRMING:
                return "That's everything?", None
            else:
                return "Sorry, say that again?", None
    
    def _update_order_items(self, new_items: List[Dict]):
        """Merge new items into current order"""
        for new_item in new_items:
            # Check if item already exists (for modifications)
            existing = None
            for i, existing_item in enumerate(self.order_items):
                if existing_item.get("name") == new_item.get("name"):
                    existing = i
                    break
            
            if existing is not None:
                # Update quantity (modification)
                self.order_items[existing]["qty"] = new_item.get("qty", 1)
                if "modifiers" in new_item:
                    self.order_items[existing]["modifiers"] = new_item.get("modifiers")
            else:
                # Add new item
                self.order_items.append(new_item)
    
    def _update_state(self, order_data: Dict):
        """Update conversation state based on order data"""
        if order_data.get("order_complete"):
            if self.state == ConversationState.TAKING_ITEMS:
                self.state = ConversationState.CONFIRMING
            elif self.state == ConversationState.CONFIRMING:
                # User confirmed
                self.state = ConversationState.CLOSING
        else:
            if self.state == ConversationState.GREETING:
                self.state = ConversationState.TAKING_ITEMS
            elif self.state == ConversationState.TAKING_ITEMS and order_data.get("items"):
                # Still taking items
                pass
    
    def _generate_confirmation(self) -> str:
        """Generate confirmation message with order summary"""
        total = sum(item.get("qty", 1) for item in self.order_items)
        return f"That's {total} items total. Look right?"
    
    def _generate_item_ack(self, items: List[Dict]) -> str:
        """Generate acknowledgment for added items"""
        if items:
            item_name = items[0].get("name", "that")
            return f"Got the {item_name}. What else?"
        return "Gotcha, anything else?"
    
    def _clean_response(self, text: str) -> str:
        """Remove formal/robotic phrases"""
        if not text:
            return text
        forbidden = ["as an ai", "i apologize", "i'm sorry", "unfortunately", 
                     "however", "furthermore", "moreover"]
        text_lower = text.lower()
        for phrase in forbidden:
            if phrase in text_lower:
                # Replace with casual alternative
                text = "Anything else for ya?"
                break
        return text
    
    def get_order_summary(self) -> Dict:
        """Returns current order summary"""
        return {
            "items": self.order_items,
            "total_items": sum(item.get("qty", 1) for item in self.order_items),
            "state": self.state.value
        }
    
    def reset(self):
        """Reset state and conversation history"""
        self.state = ConversationState.GREETING
        self.order_items = []
        self.conversation_history = []
        self.retry_count = 0
