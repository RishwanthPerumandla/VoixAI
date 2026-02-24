"""Understanding Module - Intent + Entity extraction from user input"""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Intent:
    """User intent classification"""
    primary: str  # ordering|information|service|conversation|escalation
    confidence: float
    sub_intent: str = ""  # new_order|modify_order|cancel|complaint|question


@dataclass
class Entity:
    """Extracted entity"""
    type: str  # item|quantity|flavor|modifier|time|preference|person
    value: Any
    confidence: float = 1.0
    start: int = 0
    end: int = 0


@dataclass
class Sentiment:
    """Sentiment analysis result"""
    polarity: str  # positive|neutral|negative
    urgency: str = "low"  # low|medium|high
    frustration: float = 0.0  # 0-1 scale


@dataclass
class UnderstandingResult:
    """Complete understanding of user input"""
    intent: Intent
    entities: List[Entity]
    sentiment: Sentiment
    raw_text: str
    is_question: bool = False
    is_interruption: bool = False
    is_hesitation: bool = False
    references_previous: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": {
                "primary": self.intent.primary,
                "confidence": self.intent.confidence,
                "sub_intent": self.intent.sub_intent
            },
            "entities": [
                {"type": e.type, "value": e.value, "confidence": e.confidence}
                for e in self.entities
            ],
            "sentiment": {
                "polarity": self.sentiment.polarity,
                "urgency": self.sentiment.urgency,
                "frustration": self.sentiment.frustration
            },
            "is_question": self.is_question,
            "is_interruption": self.is_interruption,
            "references_previous": self.references_previous or []
        }


class UnderstandingEngine:
    """Extracts meaning from user text input"""
    
    # Intent patterns
    INTENT_PATTERNS = {
        "ordering": [
            r'\b(order|get|want|like|need|give me|ill have|i\'ll have|can i get|lemme get)\b',
            r'\b(add|throw in|include)\b',
        ],
        "information": [
            r'\b(what|how much|price|cost|how many|which|where|when)\b',
            r'\b(do you have|is there|are there|can you)\b',
            r'\b(recommend|suggest|what\'s good)\b',
        ],
        "service": [
            r'\b(cancel|change|modify|update|remove|delete)\b',
            r'\b(wrong|incorrect|mistake|problem|issue)\b',
        ],
        "escalation": [
            r'\b(manager|supervisor|human|person|representative)\b',
            r'\b(frustrated|angry|ridiculous|unacceptable|terrible)\b',
        ],
        "conversation": [
            r'\b(hi|hello|hey|thanks|thank you|bye|goodbye)\b',
            r'\b(yes|no|yeah|nah|sure|okay|ok)\b',
        ]
    }
    
    SUB_INTENT_PATTERNS = {
        "new_order": [r'\b(start|begin|new order|place an order)\b'],
        "modify_order": [r'\b(change|switch|make it|instead of|not that)\b'],
        "cancel": [r'\b(cancel|never mind|forget it|don\'t want)\b'],
        "complaint": [r'\b(wrong|terrible|cold|bad|sucked|awful|pissed|mad)\b'],
        "question": [r'\?(what|how|which|where|when|why|is|are|do|does|can)\b'],
    }
    
    # Sentiment indicators
    POSITIVE_WORDS = ['good', 'great', 'awesome', 'love', 'perfect', 'excellent', 'amazing', 'best', 'yum', 'delicious']
    NEGATIVE_WORDS = ['bad', 'terrible', 'awful', 'hate', 'suck', 'worst', 'gross', 'cold', 'wrong', 'disgusting']
    FRUSTRATION_WORDS = ['pissed', 'angry', 'mad', 'furious', 'ridiculous', 'stupid', 'damn', 'hell', 'seriously', 'again']
    URGENCY_WORDS = ['hurry', 'quick', 'fast', 'now', 'asap', 'immediately', 'running late', 'short on time']
    
    # Entity patterns
    QUANTITY_PATTERN = r'(\d+)\s*(?:piece|pc|wing|wings)?'
    NAME_PATTERNS = [
        r'my name is (\w+)',
        r'it\'s (\w+)',
        r'this is (\w+)',
        r'(\w+) here',
        r'for (\w+)',
        r'order (?:for|in the name of) (\w+)',
        r'i\'m (\w+)',
        r'name\'s (\w+)',
    ]
    
    # Flavor mappings with fuzzy matching
    FLAVOR_MAP = {
        # Direct matches
        'lemon pepper': 'Lemon Pepper',
        'cajun': 'Cajun',
        'garlic parmesan': 'Garlic Parmesan',
        'hickory smoked bbq': 'Hickory Smoked BBQ',
        'bbq': 'Hickory Smoked BBQ',
        'barbecue': 'Hickory Smoked BBQ',
        'mild': 'Mild',
        'original hot': 'Original Hot',
        'hot': 'Original Hot',
        'atomic': 'Atomic',
        'mango habanero': 'Mango Habanero',
        'korean bbq': 'Korean BBQ',
        'korean': 'Korean BBQ',
        'spicy korean': 'Spicy Korean',
        'louisiana rub': 'Louisiana Rub',
        'louisiana': 'Louisiana Rub',
        'buffalo': 'Original Hot',
        # Fuzzy matches
        'lemon clipper': 'Lemon Pepper',
        'lemon paper': 'Lemon Pepper',
        'lemon peper': 'Lemon Pepper',
        'lemonpepper': 'Lemon Pepper',
        'cajan': 'Cajun',
        'garlic parm': 'Garlic Parmesan',
        'garlic parmesian': 'Garlic Parmesan',
        'buffalo hot': 'Atomic',
        'atomic hot': 'Atomic',
        'original': 'Original Hot',
        'louisana': 'Louisiana Rub',
        'louisianna': 'Louisiana Rub',
    }
    
    DRINKS = ['coke', 'diet coke', 'sprite', 'dr pepper', 'diet dr pepper',
              'lemonade', 'strawberry lemonade', 'mango lemonade', 'iced tea',
              'sweet tea', 'unsweetened tea', 'fruit punch']
    
    SIDES = ['seasoned fries', 'veggie sticks', 'cheese fries', 'buffalo ranch fries',
             'cajun corn', 'coleslaw', 'fries']
    
    DIPS = ['ranch', 'blue cheese', 'honey mustard', 'cheese sauce', 'teriyaki']
    
    def __init__(self):
        self.previous_entities: List[Entity] = []
    
    def understand(self, text: str, conversation_history: List[Dict] = None) -> UnderstandingResult:
        """Main entry point - analyze user input"""
        text_lower = text.lower().strip()
        
        # Classify intent
        intent = self._classify_intent(text_lower)
        
        # Extract entities
        entities = self._extract_entities(text_lower)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(text_lower)
        
        # Detect question
        is_question = '?' in text or any(
            re.search(pattern, text_lower) 
            for pattern in [r'^(what|how|which|where|when|why|is|are|do|does|can|could)']
        )
        
        # Detect hesitation
        is_hesitation = any(word in text_lower for word in ['um', 'uh', 'hmm', 'let me think', 'i guess'])
        
        # Detect references to previous
        references = self._detect_references(text_lower, conversation_history)
        
        return UnderstandingResult(
            intent=intent,
            entities=entities,
            sentiment=sentiment,
            raw_text=text,
            is_question=is_question,
            is_hesitation=is_hesitation,
            references_previous=references
        )
    
    def _classify_intent(self, text: str) -> Intent:
        """Classify primary and sub-intent"""
        scores = {}
        
        # Score each intent category
        for intent_name, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text)
                score += len(matches) * 0.3
            scores[intent_name] = min(score, 1.0)
        
        # Get primary intent
        primary = max(scores, key=scores.get)
        confidence = scores[primary]
        
        # If low confidence, default to conversation
        if confidence < 0.3:
            primary = "conversation"
            confidence = 0.5
        
        # Check for sub-intent
        sub_intent = ""
        for sub_name, patterns in self.SUB_INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    sub_intent = sub_name
                    break
            if sub_intent:
                break
        
        return Intent(primary=primary, confidence=confidence, sub_intent=sub_intent)
    
    def _extract_entities(self, text: str) -> List[Entity]:
        """Extract all entities from text"""
        entities = []
        
        # Extract quantities
        qty_matches = re.finditer(self.QUANTITY_PATTERN, text)
        for match in qty_matches:
            qty = int(match.group(1))
            if 1 <= qty <= 100:
                entities.append(Entity(
                    type="quantity",
                    value=qty,
                    start=match.start(),
                    end=match.end()
                ))
        
        # Extract names
        for pattern in self.NAME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).capitalize()
                # Filter out common false positives
                if name.lower() not in ['the', 'a', 'an', 'my', 'order', 'to', 'for']:
                    entities.append(Entity(
                        type="person",
                        value=name,
                        start=match.start(),
                        end=match.end()
                    ))
                    break  # Only take first name
        
        # Extract wing type
        if 'boneless' in text:
            entities.append(Entity(type="modifier", value="boneless"))
        elif 'bone-in' in text or 'bone in' in text:
            entities.append(Entity(type="modifier", value="bone-in"))
        
        # Extract flavors
        flavors = self._extract_flavors(text)
        for flavor in flavors:
            entities.append(Entity(type="flavor", value=flavor))
        
        # Extract drinks
        for drink in self.DRINKS:
            if drink in text:
                # Check for size
                size = "20oz"
                if '32' in text or 'large' in text:
                    size = "32oz"
                entities.append(Entity(
                    type="drink",
                    value={"name": drink, "size": size}
                ))
                break
        
        # Extract sides
        for side in self.SIDES:
            if side in text:
                entities.append(Entity(type="side", value=side))
                break
        
        # Extract dips
        for dip in self.DIPS:
            if dip in text:
                entities.append(Entity(type="dip", value=dip))
                break
        
        # Extract preferences (heat level, etc)
        heat_preference = self._extract_heat_preference(text)
        if heat_preference:
            entities.append(Entity(type="preference", value={"heat": heat_preference}))
        
        # Extract yes/no
        if any(word in text for word in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay']):
            entities.append(Entity(type="confirmation", value=True))
        elif any(word in text for word in ['no', 'nope', 'nah']):
            entities.append(Entity(type="confirmation", value=False))
        
        return entities
    
    def _extract_flavors(self, text: str) -> List[Dict]:
        """Extract wing flavors with fuzzy matching"""
        flavors = []
        
        for pattern, canonical in self.FLAVOR_MAP.items():
            if pattern in text:
                # Check if we already have this flavor
                if not any(f['name'] == canonical for f in flavors):
                    # Try to find quantity for this flavor
                    qty_match = re.search(rf'(\d+)\s+(?:of\s+)?{re.escape(pattern)}', text)
                    if qty_match:
                        qty = int(qty_match.group(1))
                    else:
                        qty = None  # Will be determined later
                    
                    flavors.append({
                        "name": canonical,
                        "qty": qty,
                        "original": pattern
                    })
        
        return flavors
    
    def _extract_heat_preference(self, text: str) -> Optional[str]:
        """Extract heat level preference"""
        heat_patterns = {
            "mild": [r'\bmild\b', r'\bnot spicy\b', r'\blight\b', r'\bsafe\b'],
            "medium": [r'\bmedium\b', r'\bsomewhere in (?:the )?middle\b', r'\blittle spicy\b'],
            "hot": [r'\bhot\b(?!\s*wings)', r'\bspicy\b', r'\bheat\b'],
            "extreme": [r'\bextreme\b', r'\batomic\b', r'\bhottest\b', r'\bnuke\b'],
        }
        
        for level, patterns in heat_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return level
        
        return None
    
    def _analyze_sentiment(self, text: str) -> Sentiment:
        """Analyze sentiment of text"""
        words = text.split()
        
        positive_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)
        frustration_count = sum(1 for w in words if w in self.FRUSTRATION_WORDS)
        urgency_count = sum(1 for w in words if w in self.URGENCY_WORDS)
        
        # Calculate polarity
        if negative_count > positive_count:
            polarity = "negative"
        elif positive_count > negative_count:
            polarity = "positive"
        else:
            polarity = "neutral"
        
        # Calculate urgency
        if urgency_count >= 2 or frustration_count >= 2:
            urgency = "high"
        elif urgency_count == 1 or frustration_count == 1:
            urgency = "medium"
        else:
            urgency = "low"
        
        # Calculate frustration score (0-1)
        frustration = min(frustration_count * 0.3 + negative_count * 0.1, 1.0)
        
        return Sentiment(
            polarity=polarity,
            urgency=urgency,
            frustration=frustration
        )
    
    def _detect_references(self, text: str, history: List[Dict] = None) -> List[str]:
        """Detect references to previous conversation topics"""
        references = []
        
        # Reference words
        ref_patterns = {
            "wings": [r'\bthose\b', r'\bthem\b', r'\bthat\b', r'\bit\b'],
            "flavor": [r'\bthat flavor\b', r'\bthe flavor\b', r'\bthat one\b'],
            "combo": [r'\bthe combo\b', r'\bthat combo\b'],
            "order": [r'\bmy order\b', r'\bthe order\b'],
        }
        
        for topic, patterns in ref_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    references.append(topic)
                    break
        
        return references
    
    def quick_intent(self, text: str) -> str:
        """Fast intent check for simple cases"""
        text_lower = text.lower().strip()
        
        # Simple patterns for quick classification
        if any(w in text_lower for w in ['yes', 'yeah', 'sure', 'okay', 'yep']):
            return "affirmation"
        elif any(w in text_lower for w in ['no', 'nope', 'nah']):
            return "negation"
        elif any(w in text_lower for w in ['hi', 'hello', 'hey']):
            return "greeting"
        elif any(w in text_lower for w in ['bye', 'goodbye', 'see ya']):
            return "farewell"
        elif '?' in text_lower:
            return "question"
        
        return "unknown"
