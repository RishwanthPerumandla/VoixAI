"""
Cartesia Text-to-Speech Processor
Streaming voice synthesis using Cartesia Sonic
"""

import asyncio
from typing import Callable, Optional
try:
    from cartesia import Cartesia
except ImportError:
    Cartesia = None

from src.config import settings


class CartesiaTTSProcessor:
    """
    Text-to-Speech processor using Cartesia Sonic
    
    Features:
    - Streaming synthesis
    - Low latency (<200ms)
    - Natural voice quality
    """
    
    def __init__(self, api_key: str = None):
        if Cartesia is None:
            raise ImportError("Cartesia SDK not installed")
        
        self.api_key = api_key or settings.cartesia_api_key
        self.client = Cartesia(api_key=self.api_key)
        
        # Voice settings
        self.voice_id = "c2ac25f9-ecc4-4f56-909e-6c5bdd3a40da"  # Default voice (change to Tasha later)
        self.model_id = "sonic-english"
        self.sample_rate = 24000
        self.speed = 1.2
        
        # Callbacks
        self.on_audio: Optional[Callable[[bytes], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # State
        self._is_speaking = False
        
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            
        Returns:
            Audio bytes (PCM, 24kHz, mono)
        """
        try:
            self._is_speaking = True
            print(f"[CartesiaTTS] Synthesizing: '{text[:50]}...' ")
            
            # Generate audio using Cartesia
            audio_chunks = []
            
            for chunk in self.client.tts.sse(
                model_id=self.model_id,
                transcript=text,
                voice_id=self.voice_id,
                stream=True,
                output_format={
                    "container": "raw",
                    "encoding": "pcm_f32le",
                    "sample_rate": self.sample_rate,
                },
            ):
                audio_chunks.append(chunk["audio"])
                
                # Stream audio as it comes in
                if self.on_audio:
                    await self._async_audio_callback(chunk["audio"])
            
            # Combine all chunks
            full_audio = b"".join(audio_chunks)
            
            self._is_speaking = False
            print(f"[CartesiaTTS] Done: {len(full_audio)} bytes")
            
            return full_audio
            
        except Exception as e:
            self._is_speaking = False
            print(f"[CartesiaTTS] Error: {e}")
            if self.on_error:
                await self._async_error(e)
            return b""
    
    async def synthesize_streaming(self, text: str):
        """
        Stream synthesis audio chunks as they arrive
        
        Args:
            text: Text to synthesize
        """
        try:
            self._is_speaking = True
            print(f"[CartesiaTTS] Streaming: '{text[:50]}...' ")
            
            chunk_count = 0
            for chunk in self.client.tts.sse(
                model_id=self.model_id,
                transcript=text,
                voice_id=self.voice_id,
                stream=True,
                output_format={
                    "container": "raw",
                    "encoding": "pcm_f32le",
                    "sample_rate": self.sample_rate,
                },
            ):
                chunk_count += 1
                if self.on_audio:
                    await self._async_audio_callback(chunk["audio"])
            
            self._is_speaking = False
            print(f"[CartesiaTTS] Streamed {chunk_count} chunks")
            
        except Exception as e:
            self._is_speaking = False
            print(f"[CartesiaTTS] Streaming error: {e}")
            if self.on_error:
                await self._async_error(e)
    
    async def _async_audio_callback(self, audio_data: bytes):
        """Async wrapper for audio callback"""
        if self.on_audio:
            await self.on_audio(audio_data)
    
    async def _async_error(self, error):
        """Async wrapper for error callback"""
        if self.on_error:
            await self.on_error(error)
    
    def is_speaking(self) -> bool:
        """Check if TTS is currently speaking"""
        return self._is_speaking
    
    def stop(self):
        """Stop current synthesis"""
        self._is_speaking = False


class MockTTSProcessor:
    """
    Mock TTS processor for testing without Cartesia API
    """
    
    def __init__(self):
        self.on_audio: Optional[Callable[[bytes], None]] = None
        self._is_speaking = False
    
    async def synthesize(self, text: str) -> bytes:
        """Mock synthesis - returns empty audio"""
        print(f"[MockTTS] Synthesizing: '{text[:50]}...' (mock)")
        self._is_speaking = True
        
        # Simulate delay
        await asyncio.sleep(0.5)
        
        # Return mock audio (silence)
        mock_audio = b"\x00" * 48000  # 1 second of silence at 24kHz
        
        if self.on_audio:
            await self._async_audio_callback(mock_audio)
        
        self._is_speaking = False
        return mock_audio
    
    async def synthesize_streaming(self, text: str):
        """Mock streaming synthesis"""
        print(f"[MockTTS] Streaming: '{text[:50]}...' (mock)")
        self._is_speaking = True
        
        # Simulate streaming with chunks
        for i in range(5):
            await asyncio.sleep(0.1)
            chunk = b"\x00" * 9600  # 0.2s of silence
            if self.on_audio:
                await self._async_audio_callback(chunk)
        
        self._is_speaking = False
    
    async def _async_audio_callback(self, audio_data: bytes):
        """Async wrapper for audio callback"""
        if self.on_audio:
            await self.on_audio(audio_data)
    
    def is_speaking(self) -> bool:
        return self._is_speaking
    
    def stop(self):
        self._is_speaking = False
