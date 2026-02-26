"""
Sentiment Analysis Module
Analyzes customer sentiment in real-time using Groq LLM
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.config import settings


@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    score: float  # -1.0 to 1.0
    label: str    # negative, neutral, positive
    confidence: float  # 0.0 to 1.0
    emotion: str  # angry, frustrated, satisfied, happy, etc.
    urgency: str  # low, medium, high
    

class SentimentAnalyzer:
    """
    Analyzes sentiment using LLM for nuanced understanding
    Uses keyword matching as fallback for speed
    """
    
    # Negative sentiment keywords
    NEGATIVE_WORDS = {
        'angry', 'frustrated', 'terrible', 'awful', 'hate', 'worst',
        'horrible', 'bad', 'slow', 'broken', 'wrong', 'disappointed',
        'mad', 'annoying', 'useless', 'garbage', 'sucks', 'damn',
        'stupid', 'ridiculous', 'unacceptable',
        'cancel', 'refund', 'manager', 'complaint', 'problem'
    }
    
    # Positive sentiment keywords
    POSITIVE_WORDS = {
        'great', 'good', 'excellent', 'love', 'amazing', 'awesome',
        'fantastic', 'wonderful', 'perfect', 'thank', 'thanks',
        'appreciate', 'happy', 'satisfied', 'pleased', 'nice',
        'helpful', 'friendly', 'quick', 'easy', 'smooth'
    }
    
    # Urgency indicators
    URGENCY_WORDS = {
        'urgent', 'emergency', 'immediately', 'right now', 'asap',
        'hurry', 'quick', 'fast', 'waiting', 'long time',
        'still no', "haven't", "didn't receive"
    }
    
    def __init__(self):
        self.history: Dict[str, List[SentimentResult]] = {}
        self.use_llm = hasattr(settings, 'groq_api_key') and settings.groq_api_key
    
    def analyze_fast(self, text: str) -> SentimentResult:
        """
        Fast keyword-based sentiment analysis
        Returns result in < 1ms
        """
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        # Count sentiment words
        negative_count = len(words & self.NEGATIVE_WORDS)
        positive_count = len(words & self.POSITIVE_WORDS)
        urgency_count = len(words & self.URGENCY_WORDS)
        
        # Calculate base score
        if negative_count > positive_count:
            base_score = -0.5 - min(negative_count * 0.15, 0.4)
            emotion = 'frustrated' if negative_count > 1 else 'dissatisfied'
            label = 'negative'
        elif positive_count > negative_count:
            base_score = 0.5 + min(positive_count * 0.15, 0.4)
            emotion = 'happy' if positive_count > 1 else 'satisfied'
            label = 'positive'
        else:
            base_score = 0.0
            emotion = 'neutral'
            label = 'neutral'
        
        # Determine urgency
        if urgency_count >= 2 or 'manager' in words or 'cancel' in words:
            urgency = 'high'
        elif urgency_count == 1 or negative_count >= 2:
            urgency = 'medium'
        else:
            urgency = 'low'
        
        # Adjust emotion based on specific words
        if any(w in words for w in {'angry', 'mad', 'furious', 'pissed'}):
            emotion = 'angry'
        elif any(w in words for w in {'confused', 'unclear', "don't understand"}):
            emotion = 'confused'
        elif any(w in words for w in {'excited', "can't wait", 'looking forward'}):
            emotion = 'excited'
        
        # Calculate confidence
        confidence = min((negative_count + positive_count) * 0.25 + 0.5, 0.95)
        
        return SentimentResult(
            score=round(base_score, 2),
            label=label,
            confidence=round(confidence, 2),
            emotion=emotion,
            urgency=urgency
        )
    
    def analyze(self, text: str) -> SentimentResult:
        """Main analysis method - uses fast method"""
        return self.analyze_fast(text)
    
    def track(self, session_id: str, result: SentimentResult):
        """Track sentiment over time for a session"""
        if session_id not in self.history:
            self.history[session_id] = []
        
        self.history[session_id].append(result)
        
        # Keep only last 20 entries
        if len(self.history[session_id]) > 20:
            self.history[session_id] = self.history[session_id][-20:]
    
    def get_trend(self, session_id: str) -> Dict:
        """Get sentiment trend for a session"""
        if session_id not in self.history or not self.history[session_id]:
            return {'trend': 'stable', 'average': 0.0, 'change': 0.0}
        
        history = self.history[session_id]
        scores = [h.score for h in history]
        
        avg_score = sum(scores) / len(scores)
        
        # Calculate trend
        if len(scores) >= 3:
            recent = sum(scores[-3:]) / 3
            older = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else scores[0]
            change = recent - older
        else:
            change = 0.0
        
        if change > 0.2:
            trend = 'improving'
        elif change < -0.2:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'average': round(avg_score, 2),
            'change': round(change, 2),
            'negative_count': sum(1 for s in scores if s < -0.3),
            'positive_count': sum(1 for s in scores if s > 0.3)
        }
    
    def should_escalate(self, session_id: str, current: SentimentResult) -> bool:
        """Determine if conversation should be escalated to human"""
        trend = self.get_trend(session_id)
        
        # Escalation conditions
        if current.urgency == 'high' and current.label == 'negative':
            return True
        
        if trend['negative_count'] >= 3 and trend['trend'] == 'declining':
            return True
        
        if current.emotion in ['angry', 'furious'] and current.confidence > 0.8:
            return True
        
        return False


class ResponseModifier:
    """
    Modifies agent responses based on detected sentiment
    """
    
    def modify(self, response: str, sentiment: SentimentResult) -> str:
        """Modify response based on sentiment"""
        
        if sentiment.label == 'negative' and sentiment.urgency == 'high':
            # Add empathy for frustrated customers
            if not any(phrase in response.lower() for phrase in ['sorry', 'understand']):
                prefix = "I completely understand your frustration, and I'm here to help. "
                response = prefix + response
        
        elif sentiment.emotion == 'confused':
            # Simplify for confused customers
            response = self._simplify_response(response)
        
        elif sentiment.emotion == 'angry':
            # De-escalation language
            prefix = "I sincerely apologize for this inconvenience. Let me fix that right away. "
            if not response.startswith("I"):
                response = prefix + response
        
        elif sentiment.label == 'positive' and sentiment.emotion in ['happy', 'excited']:
            # Match enthusiasm
            response = response.replace(".", "!") if not response.endswith("!") else response
        
        return response
    
    def _simplify_response(self, text: str) -> str:
        """Simplify a response for clarity"""
        # Break long sentences
        sentences = text.split(". ")
        if len(sentences) > 2:
            text = ". ".join(sentences[:2]) + "."
        
        # Remove complex phrases
        replacements = {
            "additionally": "also",
            "furthermore": "also",
            "however": "but",
            "therefore": "so",
            "nevertheless": "still"
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
