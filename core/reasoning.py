"""Reasoning Module - Planning and tool selection for ReAct agent"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import json


class ActionType(Enum):
    """Types of actions the agent can take"""
    GREET = "greet"
    ASK_NAME = "ask_name"
    ASK_WING_QTY = "ask_wing_qty"
    ASK_WING_TYPE = "ask_wing_type"
    ASK_FLAVOR = "ask_flavor"
    ASK_COMBO = "ask_combo"
    ASK_DRINK = "ask_drink"
    ASK_SIDE = "ask_side"
    ASK_DIP = "ask_dip"
    CONFIRM_ITEM = "confirm_item"
    CONFIRM_ORDER = "confirm_order"
    COMPLETE_ORDER = "complete_order"
    MODIFY_ORDER = "modify_order"
    ANSWER_QUESTION = "answer_question"
    CREATE_TICKET = "create_ticket"
    ESCALATE = "escalate"
    EXPRESS_EMPATHY = "express_empathy"
    UPSELL = "upsell"
    RECOVERY = "recovery"
    SMALL_TALK = "small_talk"


@dataclass
class ReActStep:
    """A single step in the ReAct loop"""
    thought: str
    action: str
    action_input: Dict
    observation: str = ""
    final_answer: str = ""
    tool_calls: List[Dict] = field(default_factory=list)


@dataclass
class ConversationContext:
    """Current conversation context"""
    stage: str = "greeting"
    current_order: Dict = field(default_factory=dict)
    customer_name: str = ""
    
    # Current item being built (persisted in current_item dict)
    # These track what we know about the CURRENT item
    has_name: bool = False
    has_wing_qty: bool = False
    has_wing_type: bool = False
    has_flavor: bool = False
    combo_offered: bool = False
    combo_decided: bool = False
    is_combo: bool = False
    has_drink: bool = False
    has_side: bool = False
    has_dip: bool = False


class ReasoningEngine:
    """Decides what to do based on understanding + context"""
    
    def __init__(self, tools: Dict[str, Callable] = None):
        self.tools = tools or {}
    
    def reason(self, understanding: Dict, context: ConversationContext, 
               current_item: Dict, history: List[Dict] = None) -> ReActStep:
        """Main reasoning entry point"""
        
        intent = understanding.get("intent", {})
        primary_intent = intent.get("primary", "conversation")
        sub_intent = intent.get("sub_intent", "")
        entities = understanding.get("entities", [])
        sentiment = understanding.get("sentiment", {})
        is_question = understanding.get("is_question", False)
        text = understanding.get("raw_text", "").lower()
        
        # Extract entities from this turn
        extracted = self._extract_entities(entities, text)
        
        # Handle high-priority situations first
        if sentiment.get("frustration", 0) > 0.7 or sentiment.get("urgency") == "high":
            return self._handle_frustration(context)
        
        if sub_intent == "complaint":
            return self._handle_complaint(understanding, context)
        
        # Update context with new info from this turn
        self._apply_extracted(context, current_item, extracted)
        
        # Handle yes/no responses
        if extracted.get("confirmation") is not None:
            return self._handle_confirmation(extracted["confirmation"], context, current_item)
        
        # Main routing
        if primary_intent == "ordering":
            return self._handle_ordering(understanding, extracted, context, current_item, text)
        
        elif primary_intent == "information" or is_question:
            return self._handle_info_request(understanding, extracted, context, text)
        
        elif primary_intent == "service":
            return self._handle_service(understanding, context)
        
        elif primary_intent == "escalation":
            return self._handle_escalation(understanding, context)
        
        else:  # conversation
            return self._handle_conversation(extracted, context, current_item, text)
    
    def _extract_entities(self, entities: List[Dict], text: str) -> Dict:
        """Extract entities from user input"""
        result = {
            "quantities": [],
            "flavors": [],
            "wing_type": None,
            "drink": None,
            "side": None,
            "dip": None,
            "name": None,
            "confirmation": None,
            "wants_combo": None,
        }
        
        for entity in entities:
            etype = entity.get("type")
            value = entity.get("value")
            
            if etype == "quantity":
                result["quantities"].append(value)
            elif etype == "flavor":
                result["flavors"].append(value)
            elif etype == "modifier" and value in ["boneless", "bone-in"]:
                result["wing_type"] = value
            elif etype == "drink":
                result["drink"] = value
            elif etype == "side":
                result["side"] = value
            elif etype == "dip":
                result["dip"] = value
            elif etype == "person":
                result["name"] = value
            elif etype == "confirmation":
                result["confirmation"] = value
        
        # Direct text checks
        if "boneless" in text:
            result["wing_type"] = "boneless"
        elif "bone-in" in text or "bone in" in text:
            result["wing_type"] = "bone-in"
        
        if "combo" in text or "make it a combo" in text:
            result["wants_combo"] = True
        elif "no combo" in text:
            result["wants_combo"] = False
        
        return result
    
    def _apply_extracted(self, context: ConversationContext, current_item: Dict, extracted: Dict):
        """Apply extracted entities to context and current_item"""
        
        if extracted.get("name"):
            context.customer_name = extracted["name"]
            context.has_name = True
        
        if extracted.get("quantities"):
            current_item["qty"] = extracted["quantities"][0]
            context.has_wing_qty = True
        
        if extracted.get("wing_type"):
            current_item["wing_type"] = extracted["wing_type"]
            context.has_wing_type = True
        
        if extracted.get("flavors"):
            current_item["flavors"] = extracted["flavors"]
            context.has_flavor = True
        
        if extracted.get("drink"):
            current_item["drink"] = extracted["drink"]
            context.has_drink = True
        
        if extracted.get("side"):
            current_item["side"] = extracted["side"]
            context.has_side = True
        
        if extracted.get("dip"):
            current_item["dip"] = extracted["dip"]
            context.has_dip = True
    
    def _get_next_action(self, context: ConversationContext, current_item: Dict) -> ReActStep:
        """Determine next action based on current state"""
        
        # Flow: Name → Qty → Type → Flavor → Combo? → Confirm
        
        if not context.has_name:
            return ReActStep(
                thought="Need customer name",
                action=ActionType.GREET.value,
                action_input={}
            )
        
        if not context.has_wing_qty:
            return ReActStep(
                thought="Need wing quantity",
                action=ActionType.ASK_WING_QTY.value,
                action_input={}
            )
        
        if not context.has_wing_type:
            qty = current_item.get("qty", 10)
            return ReActStep(
                thought=f"Have {qty} wings, need type",
                action=ActionType.ASK_WING_TYPE.value,
                action_input={"qty": qty}
            )
        
        if not context.has_flavor:
            qty = current_item.get("qty", 10)
            wing_type = current_item.get("wing_type", "wings")
            return ReActStep(
                thought=f"Have {qty} {wing_type}, need flavor",
                action=ActionType.ASK_FLAVOR.value,
                action_input={"qty": qty, "type": wing_type}
            )
        
        if not context.combo_decided:
            qty = current_item.get("qty", 10)
            if qty >= 6:
                context.combo_offered = True
                return ReActStep(
                    thought="Offer combo upsell",
                    action=ActionType.UPSELL.value,
                    action_input={"upsell_type": "combo", "qty": qty},
                    tool_calls=[{
                        "tool": "suggest_upsell",
                        "params": {"current_items": [dict(current_item)], "conversation_stage": "mid"}
                    }]
                )
            else:
                context.combo_decided = True
        
        # Item complete - add to order and confirm
        self._add_to_order(context, current_item)
        return ReActStep(
            thought="Item complete, confirm order",
            action=ActionType.CONFIRM_ORDER.value,
            action_input={},
            tool_calls=[{
                "tool": "calculate_price",
                "params": {"items": context.current_order.get("items", [])}
            }]
        )
    
    def _add_to_order(self, context: ConversationContext, current_item: Dict):
        """Add current item to order and reset current item"""
        if not current_item or not current_item.get("qty"):
            return
        
        item = {
            "name": f"{current_item.get('wing_type', 'Bone-In')} Wings",
            "qty": current_item["qty"],
            "category": "wings",
            "modifiers": {
                "flavors": current_item.get("flavors", []),
                "type": current_item.get("wing_type", "bone-in")
            },
            "unit_price": 1.29
        }
        
        if context.is_combo:
            item["is_combo"] = True
        
        if "items" not in context.current_order:
            context.current_order["items"] = []
        context.current_order["items"].append(item)
    
    def _handle_confirmation(self, confirmed: bool, context: ConversationContext, 
                            current_item: Dict) -> ReActStep:
        """Handle yes/no"""
        
        if context.stage == "confirming" and confirmed:
            return ReActStep(
                thought="Order confirmed, complete it",
                action=ActionType.COMPLETE_ORDER.value,
                action_input={},
                tool_calls=[{"tool": "calculate_price", "params": {"items": context.current_order.get("items", [])}}]
            )
        
        if context.combo_offered and not context.combo_decided:
            context.combo_decided = True
            context.is_combo = confirmed
            
            if confirmed:
                return ReActStep(
                    thought="Combo accepted, ask for drink",
                    action=ActionType.ASK_DRINK.value,
                    action_input={}
                )
            else:
                self._add_to_order(context, current_item)
                return ReActStep(
                    thought="Combo declined, confirm order",
                    action=ActionType.CONFIRM_ORDER.value,
                    action_input={},
                    tool_calls=[{"tool": "calculate_price", "params": {"items": context.current_order.get("items", [])}}]
                )
        
        return self._get_next_action(context, current_item)
    
    def _handle_ordering(self, understanding: Dict, extracted: Dict,
                        context: ConversationContext, current_item: Dict, text: str) -> ReActStep:
        """Handle ordering intent"""
        
        # If we got a name, handle it
        if extracted.get("name") and not context.has_name:
            context.has_name = True
            context.customer_name = extracted["name"]
            return ReActStep(
                thought=f"Got name: {extracted['name']}",
                action=ActionType.GREET.value,
                action_input={"name": extracted["name"]}
            )
        
        # Check if saying just a number (like "10")
        if extracted.get("quantities") and len(extracted) == 1 and not context.has_wing_qty:
            qty = extracted["quantities"][0]
            current_item["qty"] = qty
            context.has_wing_qty = True
            return ReActStep(
                thought=f"Got quantity {qty}, need type",
                action=ActionType.ASK_WING_TYPE.value,
                action_input={"qty": qty}
            )
        
        # Check for combo order
        if extracted.get("wants_combo"):
            qty = extracted["quantities"][0] if extracted.get("quantities") else 10
            current_item.clear()
            current_item.update({
                "qty": qty,
                "type": extracted.get("wing_type") or "bone-in",
                "is_combo": True,
                "flavors": extracted.get("flavors", [])
            })
            context.has_wing_qty = True
            if extracted.get("wing_type"):
                context.has_wing_type = True
            context.is_combo = True
            context.combo_decided = True
            
            if not extracted.get("flavors"):
                return ReActStep(
                    thought=f"Combo {qty}pc, need flavor",
                    action=ActionType.ASK_FLAVOR.value,
                    action_input={"qty": qty, "type": current_item["type"]}
                )
            return ReActStep(
                thought="Combo with flavor, ask drink",
                action=ActionType.ASK_DRINK.value,
                action_input={}
            )
        
        # Regular flow
        return self._get_next_action(context, current_item)
    
    def _handle_conversation(self, extracted: Dict, context: ConversationContext,
                            current_item: Dict, text: str) -> ReActStep:
        """Handle conversation"""
        
        # Check for name
        if extracted.get("name") and not context.has_name:
            context.has_name = True
            context.customer_name = extracted["name"]
            return ReActStep(
                thought=f"Got name: {extracted['name']}",
                action=ActionType.GREET.value,
                action_input={"name": extracted["name"]}
            )
        
        # Check for just a number
        if extracted.get("quantities") and not context.has_wing_qty:
            qty = extracted["quantities"][0]
            current_item["qty"] = qty
            context.has_wing_qty = True
            return ReActStep(
                thought=f"Got {qty}, need type",
                action=ActionType.ASK_WING_TYPE.value,
                action_input={"qty": qty}
            )
        
        # Greeting
        if any(w in text for w in ["hi", "hello", "hey"]):
            if context.has_name:
                return ReActStep(
                    thought=f"Greeting from {context.customer_name}",
                    action=ActionType.GREET.value,
                    action_input={"name": context.customer_name}
                )
            return ReActStep(
                thought="Greeting, need name",
                action=ActionType.GREET.value,
                action_input={}
            )
        
        # Unsure
        if any(p in text for p in ["don't know", "not sure", "what do you recommend"]):
            return ReActStep(
                thought="Customer unsure, give recommendations",
                action=ActionType.ANSWER_QUESTION.value,
                action_input={"query_type": "recommendation"},
                tool_calls=[{"tool": "search_menu", "params": {"category": "flavor", "limit": 3}}]
            )
        
        # Default - continue flow
        return self._get_next_action(context, current_item)
    
    def _handle_info_request(self, understanding: Dict, extracted: Dict,
                            context: ConversationContext, text: str) -> ReActStep:
        """Handle info requests"""
        
        if any(w in text for w in ["price", "cost", "how much"]):
            return ReActStep(
                thought="Pricing question",
                action=ActionType.ANSWER_QUESTION.value,
                action_input={"query_type": "pricing"},
                tool_calls=[{"tool": "calculate_price", "params": {"items": context.current_order.get("items", [])}}]
            )
        
        if any(w in text for w in ["recommend", "suggest", "what's good", "popular", "famous"]):
            return ReActStep(
                thought="Recommendation request",
                action=ActionType.ANSWER_QUESTION.value,
                action_input={"query_type": "recommendation"},
                tool_calls=[{"tool": "search_menu", "params": {"category": "flavor", "limit": 5}}]
            )
        
        return ReActStep(
            thought="General menu question",
            action=ActionType.ANSWER_QUESTION.value,
            action_input={"query": text},
            tool_calls=[{"tool": "search_menu", "params": {"query": text, "limit": 5}}]
        )
    
    def _handle_service(self, understanding: Dict, context: ConversationContext) -> ReActStep:
        """Handle service requests"""
        sub_intent = understanding.get("intent", {}).get("sub_intent", "")
        
        if sub_intent == "cancel":
            return ReActStep(
                thought="Cancel and reset",
                action=ActionType.RECOVERY.value,
                action_input={"message": "No problem, starting fresh. What can I get you?"}
            )
        
        return ReActStep(
            thought="Service request",
            action=ActionType.ASK_CLARIFICATION.value,
            action_input={}
        )
    
    def _handle_frustration(self, context: ConversationContext) -> ReActStep:
        return ReActStep(
            thought="Customer frustrated",
            action=ActionType.EXPRESS_EMPATHY.value,
            action_input={"empathy_type": "frustration"}
        )
    
    def _handle_complaint(self, understanding: Dict, context: ConversationContext) -> ReActStep:
        return ReActStep(
            thought="Complaint received",
            action=ActionType.CREATE_TICKET.value,
            action_input={"ticket_type": "complaint", "severity": "high"},
            tool_calls=[{
                "tool": "create_ticket",
                "params": {"ticket_type": "complaint", "description": understanding.get("raw_text", ""), "severity": "high"}
            }]
        )
    
    def _handle_escalation(self, understanding: Dict, context: ConversationContext) -> ReActStep:
        return ReActStep(
            thought="Escalate to human",
            action=ActionType.ESCALATE.value,
            action_input={"reason": "customer_request", "urgency": "normal"},
            tool_calls=[{
                "tool": "escalate_to_human",
                "params": {"reason": "customer_request", "urgency": "normal", "context_summary": f"Stage: {context.stage}"}
            }]
        )
