"""Interrupt Handler - Barge-in detection and handling"""
import random
import numpy as np
from typing import Callable, Optional
from enum import Enum
import time


class InterruptType(Enum):
    """Types of interruptions"""
    NONE = "none"
    ENERGY_SPIKE = "energy_spike"
    STOP_WORD = "stop_word"
    QUESTION_TONE = "question_tone"


class InterruptHandler:
    """
    Dual-path audio processing for interrupt detection.
    
    Fast path: Energy-based detection (~50ms)
    Slow path: ASR-based confirmation (~300-500ms)
    """
    
    # Stop words that trigger immediate interruption
    STOP_WORDS = ['stop', 'wait', 'hold on', 'hold up', 'no no', 'hey', 'excuse me']
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 energy_threshold: float = 0.7,
                 silence_threshold_ms: int = 300):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_samples = int(silence_threshold_ms * sample_rate / 1000)
        
        self.is_speaking = False
        self.interrupt_detected = False
        self.last_interrupt_time = 0
        self.cooldown_ms = 500  # Minimum time between interrupts
        
        # Energy tracking
        self.recent_energy = []
        self.energy_window_size = 10
        
    def process_audio(self, audio_chunk: np.ndarray) -> InterruptType:
        """
        Process audio chunk for interrupt detection.
        Returns interrupt type if detected.
        """
        # Calculate RMS energy
        energy = np.sqrt(np.mean(audio_chunk ** 2))
        
        # Update energy window
        self.recent_energy.append(energy)
        if len(self.recent_energy) > self.energy_window_size:
            self.recent_energy.pop(0)
        
        # Check cooldown
        current_time = time.time() * 1000
        if current_time - self.last_interrupt_time < self.cooldown_ms:
            return InterruptType.NONE
        
        # Check for energy spike during TTS playback
        if len(self.recent_energy) >= 3:
            recent_avg = np.mean(self.recent_energy[-3:])
            if recent_avg > self.energy_threshold:
                self.interrupt_detected = True
                self.last_interrupt_time = current_time
                return InterruptType.ENERGY_SPIKE
        
        return InterruptType.NONE
    
    def check_text_for_interrupt(self, text: str) -> InterruptType:
        """
        Check transcribed text for interrupt signals.
        Called after ASR in slow path.
        """
        text_lower = text.lower().strip()
        
        # Check stop words
        for word in self.STOP_WORDS:
            if word in text_lower:
                self.interrupt_detected = True
                self.last_interrupt_time = time.time() * 1000
                return InterruptType.STOP_WORD
        
        # Check for question intonation patterns
        if text_lower.endswith('?'):
            return InterruptType.QUESTION_TONE
        
        return InterruptType.NONE
    
    def should_interrupt(self, audio_chunk: np.ndarray = None, text: str = None) -> InterruptType:
        """
        Main entry point for interrupt checking.
        Can use fast path (audio only) or slow path (with text).
        """
        # Fast path - energy detection
        if audio_chunk is not None:
            result = self.process_audio(audio_chunk)
            if result != InterruptType.NONE:
                return result
        
        # Slow path - text analysis
        if text is not None:
            return self.check_text_for_interrupt(text)
        
        return InterruptType.NONE
    
    def get_interrupt_acknowledgment(self, interrupt_type: InterruptType) -> str:
        """Get appropriate acknowledgment for interrupt type"""
        acknowledgments = {
            InterruptType.ENERGY_SPIKE: "Yeah?",
            InterruptType.STOP_WORD: "Sorry, go ahead.",
            InterruptType.QUESTION_TONE: "What's up?",
        }
        return acknowledgments.get(interrupt_type, "Yeah?")
    
    def reset(self):
        """Reset interrupt state"""
        self.interrupt_detected = False
        self.recent_energy = []
        self.is_speaking = False


class BackchannelGenerator:
    """Generates backchannel responses while listening"""
    
    BACKCHANNELS = [
        "mm-hmm",
        "yeah",
        "got it",
        "uh-huh",
        "right",
        "okay",
    ]
    
    def __init__(self, min_interval_ms: int = 2000):
        self.min_interval_ms = min_interval_ms
        self.last_backchannel_time = 0
        self.engagement_level = 0.5  # 0-1 scale
    
    def should_backchannel(self, audio_chunk: np.ndarray = None) -> bool:
        """Determine if we should emit a backchannel now"""
        current_time = time.time() * 1000
        
        # Minimum interval check
        if current_time - self.last_backchannel_time < self.min_interval_ms:
            return False
        
        # If we have audio, check for natural pause
        if audio_chunk is not None:
            energy = np.sqrt(np.mean(audio_chunk ** 2))
            # Backchannel during sustained speech (medium energy)
            if 0.1 < energy < 0.5:
                return random.random() < self.engagement_level * 0.3
        
        return False
    
    def get_backchannel(self) -> str:
        """Get a backchannel response"""
        self.last_backchannel_time = time.time() * 1000
        return random.choice(self.BACKCHANNELS)


import random
