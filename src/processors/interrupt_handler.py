"""
Interrupt Handler (Barge-in Detection)
Handles user interruptions during bot speech
"""

import asyncio
from enum import Enum
from typing import Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


class InterruptState(Enum):
    IDLE = "idle"
    BOT_SPEAKING = "bot_speaking"
    INTERRUPTED = "interrupted"
    COOLDOWN = "cooldown"


@dataclass
class InterruptEvent:
    """Represents an interruption event"""
    timestamp: datetime
    transcript: str
    confidence: float
    interrupt_type: str  # "full", "partial", "keyword"


class InterruptHandler:
    """
    Handles barge-in detection and response
    """
    
    # Keywords that strongly indicate interruption
    INTERRUPTION_KEYWORDS = [
        "stop", "wait", "hold on", "pause", "no", "cancel",
        "actually", "change", "different", "not that", "wrong"
    ]
    
    def __init__(self):
        self.state = InterruptState.IDLE
        self.current_bot_task: Optional[asyncio.Task] = None
        self.interrupt_callbacks: list[Callable] = []
        self.resume_callbacks: list[Callable] = []
        
        # Detection parameters
        self.min_confidence = 0.6
        self.cooldown_duration = 1.0  # seconds after interrupt
        self.last_interrupt_time: Optional[datetime] = None
        
        # Audio level tracking
        self.speech_start_time: Optional[datetime] = None
        self.bot_speech_start_time: Optional[datetime] = None
    
    def register_interrupt_callback(self, callback: Callable):
        """Register callback for interrupt events"""
        self.interrupt_callbacks.append(callback)
    
    def register_resume_callback(self, callback: Callable):
        """Register callback for resume events"""
        self.resume_callbacks.append(callback)
    
    def on_bot_start_speaking(self):
        """Called when bot starts speaking"""
        self.state = InterruptState.BOT_SPEAKING
        self.bot_speech_start_time = datetime.now()
        print("[Interrupt] Bot speaking started")
    
    def on_bot_stop_speaking(self):
        """Called when bot stops speaking"""
        if self.state != InterruptState.INTERRUPTED:
            self.state = InterruptState.IDLE
        self.bot_speech_start_time = None
        print("[Interrupt] Bot speaking stopped")
    
    def detect_interruption(self, transcript: str, is_final: bool, confidence: float) -> bool:
        """
        Detect if user is interrupting bot speech
        Returns True if interrupt detected
        """
        # Only check during bot speaking
        if self.state != InterruptState.BOT_SPEAKING:
            return False
        
        # Skip low confidence transcriptions
        if confidence < self.min_confidence:
            return False
        
        transcript_lower = transcript.lower().strip()
        
        # Check for interruption keywords
        for keyword in self.INTERRUPTION_KEYWORDS:
            if keyword in transcript_lower:
                print(f"[Interrupt] Keyword detected: '{keyword}'")
                return True
        
        # Check for substantial speech (more than 3 words)
        if is_final and len(transcript_lower.split()) >= 3:
            print("[Interrupt] Substantial speech detected")
            return True
        
        return False
    
    async def handle_interrupt(self, transcript: str, confidence: float) -> InterruptEvent:
        """
        Handle detected interruption
        """
        event = InterruptEvent(
            timestamp=datetime.now(),
            transcript=transcript,
            confidence=confidence,
            interrupt_type="keyword" if any(k in transcript.lower() for k in self.INTERRUPTION_KEYWORDS) else "speech"
        )
        
        self.state = InterruptState.INTERRUPTED
        self.last_interrupt_time = datetime.now()
        
        print(f"[Interrupt] Handled: '{transcript[:50]}...'")
        
        # Notify callbacks
        for callback in self.interrupt_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                print(f"[Interrupt] Callback error: {e}")
        
        # Enter cooldown
        await self._enter_cooldown()
        
        return event
    
    async def _enter_cooldown(self):
        """Enter cooldown period after interrupt"""
        self.state = InterruptState.COOLDOWN
        print(f"[Interrupt] Entering cooldown ({self.cooldown_duration}s)")
        
        await asyncio.sleep(self.cooldown_duration)
        
        self.state = InterruptState.IDLE
        print("[Interrupt] Cooldown complete")
        
        # Notify resume callbacks
        for callback in self.resume_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                print(f"[Interrupt] Resume callback error: {e}")
    
    def is_interruptable(self) -> bool:
        """Check if current state allows interruption"""
        return self.state == InterruptState.BOT_SPEAKING
    
    def get_status(self) -> dict:
        """Get current handler status"""
        return {
            "state": self.state.value,
            "bot_speaking": self.state == InterruptState.BOT_SPEAKING,
            "can_interrupt": self.is_interruptable(),
            "last_interrupt": self.last_interrupt_time.isoformat() if self.last_interrupt_time else None
        }


class SmartBargeIn:
    """
    Advanced barge-in with context awareness
    """
    
    def __init__(self):
        self.handler = InterruptHandler()
        self.partial_buffer = ""
        self.min_partial_words = 2  # Min words before considering partial
    
    def process_partial(self, transcript: str, confidence: float) -> bool:
        """
        Process partial transcription for early interruption
        Returns True if interrupt should be triggered
        """
        self.partial_buffer = transcript
        
        # Check for strong interruption keywords even in partial
        transcript_lower = transcript.lower()
        strong_keywords = ["stop", "no", "cancel", "wait"]
        
        for keyword in strong_keywords:
            if keyword in transcript_lower and confidence > 0.7:
                return True
        
        return False
    
    def process_final(self, transcript: str, confidence: float) -> bool:
        """Process final transcription"""
        self.partial_buffer = ""
        return self.handler.detect_interruption(transcript, True, confidence)
    
    def should_abort_utterance(self, transcript: str) -> bool:
        """
        Determine if current bot utterance should be aborted
        based on interrupt content
        """
        transcript_lower = transcript.lower()
        
        # Always abort for these
        abort_triggers = ["stop", "cancel", "hang up", "quit", "exit"]
        for trigger in abort_triggers:
            if trigger in transcript_lower:
                return True
        
        # Abort for substantial corrections
        correction_phrases = ["actually", "i meant", "no i want", "not that", "change"]
        for phrase in correction_phrases:
            if phrase in transcript_lower:
                return True
        
        return False
    
    def get_interrupt_response(self, transcript: str) -> Optional[str]:
        """
        Generate appropriate response to interruption
        """
        transcript_lower = transcript.lower()
        
        if any(w in transcript_lower for w in ["stop", "cancel"]):
            return "Of course, let me start over. What can I help you with?"
        
        if "wait" in transcript_lower or "hold on" in transcript_lower:
            return "Sure, I'll wait. Just let me know when you're ready."
        
        if any(w in transcript_lower for w in ["actually", "change", "different"]):
            return "No problem! What would you like to change?"
        
        if "repeat" in transcript_lower or "what" in transcript_lower:
            return "I'd be happy to repeat that for you."
        
        return "I'm listening. What would you like?"


class InterruptionResistantPipeline:
    """
    Pipeline wrapper that handles interruptions gracefully
    """
    
    def __init__(self, base_pipeline):
        self.pipeline = base_pipeline
        self.barge_in = SmartBargeIn()
        self.interrupted_utterance = None
        self.is_speaking = False
    
    async def on_user_speech(self, transcript: str, is_final: bool, confidence: float):
        """Process user speech with interruption detection"""
        
        # Check for interruption
        should_interrupt = False
        
        if is_final:
            should_interrupt = self.barge_in.process_final(transcript, confidence)
        else:
            should_interrupt = self.barge_in.process_partial(transcript, confidence)
        
        if should_interrupt and self.is_speaking:
            # Handle interruption
            await self.barge_in.handler.handle_interrupt(transcript, confidence)
            
            # Cancel current speech
            await self._cancel_speech()
            
            # Get interrupt response
            response = self.barge_in.get_interrupt_response(transcript)
            
            # Check if we should abort or adapt
            if self.barge_in.should_abort_utterance(transcript):
                # Full reset
                self.interrupted_utterance = None
                return {"type": "interrupt", "action": "abort", "response": response}
            else:
                # Pause and adapt
                return {"type": "interrupt", "action": "adapt", "response": response, "new_input": transcript}
        
        # Normal processing
        return {"type": "normal", "transcript": transcript}
    
    async def _cancel_speech(self):
        """Cancel current bot speech"""
        self.is_speaking = False
        # Signal pipeline to stop TTS
        if hasattr(self.pipeline, 'cancel_tts'):
            await self.pipeline.cancel_tts()
    
    async def on_bot_speech_start(self):
        """Called when bot starts speaking"""
        self.is_speaking = True
        self.barge_in.handler.on_bot_start_speaking()
    
    async def on_bot_speech_end(self):
        """Called when bot finishes speaking"""
        self.is_speaking = False
        self.barge_in.handler.on_bot_stop_speaking()
