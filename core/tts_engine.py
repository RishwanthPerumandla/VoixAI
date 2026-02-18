"""Text-to-Speech Engine using Kokoro"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import io
import time
import numpy as np
import soundfile as sf
from kokoro import KPipeline


class TTSEngine:
    """Kokoro-based text-to-speech optimized for speed"""
    
    def __init__(self, voice: str = "af_bella", speed: float = 1.1, sample_rate: int = 24000):
        """Initialize Kokoro pipeline"""
        self.voice = voice
        self.speed = speed
        self.sample_rate = sample_rate
        
        # Initialize Kokoro pipeline (American English)
        self.pipeline = KPipeline(lang_code='a')
        
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to WAV bytes.
        Returns: WAV file bytes (24kHz, 16-bit PCM)
        """
        start_time = time.time()
        
        # Clean text - remove SSML tags that Kokoro doesn't handle well
        processed_text = text.replace("<break time='150ms'/>", ", ")
        processed_text = processed_text.replace("<break time='150ms'>", ", ")
        
        print(f"[TTS] Synthesizing: '{text[:50]}...'")
        
        # Generate audio with Kokoro
        audio_chunks = []
        
        # Use pipeline to generate
        generator = self.pipeline(
            processed_text,
            voice=self.voice,
            speed=self.speed,
            split_pattern=r'\n+'
        )
        
        for _, _, audio in generator:
            audio_chunks.append(audio)
        
        # Concatenate all chunks
        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
        else:
            # Fallback silence
            full_audio = np.zeros(int(self.sample_rate * 0.5), dtype=np.float32)
        
        # Convert to int16
        audio_int16 = (full_audio * 32767).astype(np.int16)
        
        # Write to WAV bytes
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_int16, self.sample_rate, format='WAV', subtype='PCM_16')
        wav_bytes = wav_buffer.getvalue()
        
        elapsed = time.time() - start_time
        print(f"[TTS] Done in {elapsed:.2f}s, generated {len(wav_bytes)} bytes")
        
        return wav_bytes
