"""Text-to-Speech Engine using Kokoro ONNX (faster)"""
import os
import io
import time
import urllib.request
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

# Model URLs
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


def download_file(url: str, path: str):
    """Download file if not exists"""
    if os.path.exists(path):
        return
    print(f"[TTS] Downloading {os.path.basename(path)}...")
    urllib.request.urlretrieve(url, path)
    print(f"[TTS] Downloaded {path}")


class TTSEngineONNX:
    """Kokoro ONNX-based TTS - optimized for speed"""
    
    # Cache for common phrases
    _cache = {}
    _max_cache_size = 100
    
    # Common phrases to pre-cache
    COMMON_PHRASES = [
        "Hey! Welcome to Wingstop! I'm Tasha. How many wings can I get started for you? Bone-in or boneless?",
        "Gotcha. Bone-in or boneless?",
        "What flavors are we feeling?",
        "Make it a combo with fries and a drink?",
        "What size drink?",
        "Fries or veggie sticks?",
        "What dip you want?",
        "That look right?",
        "Thanks! Pull up to the window!",
    ]
    
    def __init__(self, voice: str = "af_bella", speed: float = 1.2):
        """Initialize Kokoro ONNX - downloads model on first run"""
        self.voice = voice
        self.speed = speed
        self.sample_rate = 24000
        
        # Download models if needed
        download_file(MODEL_URL, "kokoro-v1.0.onnx")
        download_file(VOICES_URL, "voices-v1.0.bin")
        
        # Initialize Kokoro ONNX
        print("[TTS] Loading Kokoro ONNX...")
        start = time.time()
        self.kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
        print(f"[TTS] Loaded in {time.time() - start:.2f}s")
        
        # Pre-cache common phrases in background
        self._precache_common_phrases()
    
    def _precache_common_phrases(self):
        """Pre-cache common phrases for instant response"""
        print("[TTS] Pre-caching common phrases...")
        for phrase in self.COMMON_PHRASES:
            try:
                samples, sample_rate = self.kokoro.create(
                    phrase,
                    voice=self.voice,
                    speed=self.speed,
                    lang="en-us"
                )
                audio_int16 = (samples * 32767).astype(np.int16)
                wav_buffer = io.BytesIO()
                sf.write(wav_buffer, audio_int16, sample_rate, format='WAV', subtype='PCM_16')
                self._cache[phrase.lower()] = wav_buffer.getvalue()
            except Exception as e:
                print(f"[TTS] Failed to cache phrase: {e}")
        print(f"[TTS] Pre-cached {len(self._cache)} phrases")
        
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to WAV bytes using ONNX.
        Returns: WAV file bytes (24kHz, 16-bit PCM)
        """
        start_time = time.time()
        
        # Clean text
        text = text.strip()
        if not text:
            text = "Hello"
        
        # Check cache for short phrases
        cache_key = text.lower()
        if len(text) < 100 and cache_key in self._cache:
            print(f"[TTS] Cache hit: '{text[:50]}...'")
            return self._cache[cache_key]
        
        print(f"[TTS] Synthesizing: '{text[:50]}...'")
        
        # Generate audio with Kokoro ONNX
        samples, sample_rate = self.kokoro.create(
            text,
            voice=self.voice,
            speed=self.speed,
            lang="en-us"
        )
        
        # Convert to int16
        audio_int16 = (samples * 32767).astype(np.int16)
        
        # Write to WAV bytes
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_int16, sample_rate, format='WAV', subtype='PCM_16')
        wav_bytes = wav_buffer.getvalue()
        
        # Cache short phrases
        if len(text) < 100 and len(self._cache) < self._max_cache_size:
            self._cache[cache_key] = wav_bytes
        
        elapsed = time.time() - start_time
        audio_duration = len(samples) / sample_rate
        rt_factor = audio_duration / elapsed if elapsed > 0 else 0
        print(f"[TTS] Done in {elapsed:.2f}s ({audio_duration:.2f}s audio, {rt_factor:.1f}x RT)")
        
        return wav_bytes
