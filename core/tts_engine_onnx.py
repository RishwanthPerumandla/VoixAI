"""Text-to-Speech Engine using Kokoro ONNX (faster)"""
import os
import io
import time
import urllib.request
import numpy as np
import soundfile as sf

# Model URLs
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices.json"

# Ensure UTF-8 encoding for file operations on Windows
import sys
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')


def download_file(url: str, path: str):
    """Download file if not exists"""
    if os.path.exists(path):
        return
    print(f"[TTS] Downloading {os.path.basename(path)}...")
    urllib.request.urlretrieve(url, path)
    print(f"[TTS] Downloaded {path}")


def create_voices_json_if_needed():
    """Create voices.json if it doesn't exist (needed for Windows)"""
    voices_json_path = "voices.json"
    if not os.path.exists(voices_json_path):
        voices = [
            "af_bella", "af_sarah", "af_nicole", "af_sky",
            "am_adam", "am_michael",
            "bf_emma", "bf_isabella",
            "bm_george", "bm_lewis"
        ]
        import json
        with open(voices_json_path, 'w', encoding='utf-8') as f:
            json.dump(voices, f)


class TTSEngineONNX:
    """Kokoro ONNX-based TTS - optimized for speed"""
    
    # Cache for common phrases
    _cache = {}
    _max_cache_size = 100
    
    # Common phrases to pre-cache
    COMMON_PHRASES = [
        "Hey! Welcome to Wingstop! I'm Tasha. How many wings can I get started for you?",
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
        
        # Create voices.json if needed (Windows fix)
        create_voices_json_if_needed()
        
        # Download models if needed
        download_file(MODEL_URL, "kokoro-v1.0.onnx")
        download_file(VOICES_URL, "voices.json")
        
        # Initialize Kokoro ONNX with error handling
        print("[TTS] Loading Kokoro ONNX...")
        start = time.time()
        
        try:
            from kokoro_onnx import Kokoro
            self.kokoro = Kokoro("kokoro-v1.0.onnx", "voices.json")
            print(f"[TTS] Loaded in {time.time() - start:.2f}s")
        except Exception as e:
            print(f"[TTS] Error loading Kokoro: {e}")
            print("[TTS] Attempting fix with config.json...")
            self._create_config_json()
            from kokoro_onnx import Kokoro
            self.kokoro = Kokoro("kokoro-v1.0.onnx", "voices.json")
            print(f"[TTS] Loaded in {time.time() - start:.2f}s")
        
        # Pre-cache common phrases in background
        self._precache_common_phrases()
    
    def _create_config_json(self):
        """Create config.json if missing"""
        import json
        config = {
            "voices": [
                {"name": "af_bella", "language": "en-us", "gender": "female"},
                {"name": "af_sarah", "language": "en-us", "gender": "female"},
                {"name": "af_nicole", "language": "en-us", "gender": "female"},
                {"name": "af_sky", "language": "en-us", "gender": "female"},
                {"name": "am_adam", "language": "en-us", "gender": "male"},
                {"name": "am_michael", "language": "en-us", "gender": "male"},
            ]
        }
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump(config, f)
    
    def _precache_common_phrases(self):
        """Pre-cache common phrases for instant response"""
        print("[TTS] Pre-caching common phrases...")
        for phrase in self.COMMON_PHRASES:
            try:
                result = self.kokoro.create(
                    phrase,
                    voice=self.voice,
                    speed=self.speed,
                    lang="en-us"
                )
                # Handle different return formats
                if isinstance(result, tuple):
                    samples, sample_rate = result
                elif isinstance(result, dict):
                    samples = result.get('audio')
                    sample_rate = result.get('sample_rate', 24000)
                else:
                    samples = result
                    sample_rate = 24000
                    
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
        result = self.kokoro.create(
            text,
            voice=self.voice,
            speed=self.speed,
            lang="en-us"
        )
        
        # Handle different return formats
        if isinstance(result, tuple):
            samples, sample_rate = result
        elif isinstance(result, dict):
            samples = result.get('audio')
            sample_rate = result.get('sample_rate', 24000)
        else:
            samples = result
            sample_rate = 24000
        
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
