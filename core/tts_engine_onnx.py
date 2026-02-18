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
    """Kokoro ONNX-based TTS - significantly faster on CPU"""
    
    def __init__(self, voice: str = "af_bella", speed: float = 1.0):
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
        
        elapsed = time.time() - start_time
        print(f"[TTS] Done in {elapsed:.2f}s ({len(samples)/sample_rate:.2f}s audio)")
        
        return wav_bytes
