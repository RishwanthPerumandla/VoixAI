"""Speech-to-Text Engine using faster-whisper"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
from faster_whisper import WhisperModel


class STTEngine:
    """Whisper-based speech recognition optimized for CPU"""
    
    def __init__(self, model_size: str = "tiny.en", device: str = "cpu", 
                 compute_type: str = "int8", language: str = "en"):
        """Load faster-whisper model"""
        self.language = language
        # Use CPU-specific optimizations
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=4  # Optimize for quad-core CPU
        )
        
    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio array to text - optimized for speed.
        Returns cleaned text string.
        """
        # faster-whisper expects audio as numpy array
        # Optimized settings for lowest latency:
        # - no VAD filter (saves time)
        # - no previous text conditioning (saves time)
        # - temperature=0 (greedy, faster)
        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            vad_filter=False,  # Disabled for speed
            condition_on_previous_text=False,  # Disabled for speed
            beam_size=1,
            best_of=1,
            temperature=0.0,  # Greedy decoding
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6
        )
        
        # Collect all segment text
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
            
        text = " ".join(text_parts).strip()
        
        # Clean up
        text = text.replace("  ", " ")
        
        return text
