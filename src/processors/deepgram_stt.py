"""
Deepgram Speech-to-Text Processor - Real Implementation
Real-time streaming transcription using Deepgram Nova 2
"""

import asyncio
import json
from typing import Callable, Optional

from src.config import settings

# Deepgram SDK v6
try:
    from deepgram import AsyncDeepgramClient
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False
    AsyncDeepgramClient = None


class DeepgramSTTProcessor:
    """
    Speech-to-Text processor using Deepgram Nova 2
    
    Features:
    - Streaming transcription
    - Interim and final results
    - Low latency (<300ms)
    """
    
    def __init__(self, api_key: str = None):
        if not DEEPGRAM_AVAILABLE:
            raise ImportError("Deepgram SDK not installed")
        
        self.api_key = api_key or settings.deepgram_api_key
        self.client = AsyncDeepgramClient(api_key=self.api_key)
        self.connection = None
        
        # Callbacks
        self.on_transcript: Optional[Callable[[str, bool], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # State
        self._is_listening = False
        self._final_buffer = ""
        
    async def start(self):
        """Start the STT connection"""
        try:
            # Connect to live transcription - use async with for context manager
            self._connection_ctx = self.client.listen.v1.connect(
                model="nova-2",
                language="en-US",
                smart_format="true",
                interim_results="true",
                punctuate="true",
                endpointing="300",
            )
            self.connection = await self._connection_ctx.__aenter__()
            
            self._is_listening = True
            print("[DeepgramSTT] Started listening")
            return True
                
        except Exception as e:
            print(f"[DeepgramSTT] Error starting: {e}")
            import traceback
            traceback.print_exc()
            if self.on_error:
                await self.on_error(e)
            return False
    
    async def _listen(self):
        """Listen for transcripts in background"""
        try:
            async for msg in self.connection:
                self._handle_message(msg)
        except Exception as e:
            print(f"[DeepgramSTT] Listen error: {e}")
    
    def _handle_message(self, msg):
        """Handle message from Deepgram"""
        try:
            if hasattr(msg, 'type') and msg.type == "Results":
                # Extract transcript
                channel = msg.channel if hasattr(msg, 'channel') else {}
                alternatives = channel.alternatives if hasattr(channel, 'alternatives') else []
                
                if alternatives:
                    alt = alternatives[0]
                    transcript = alt.transcript if hasattr(alt, 'transcript') else ""
                    is_final = msg.is_final if hasattr(msg, 'is_final') else False
                    
                    if transcript.strip():
                        if is_final:
                            self._final_buffer += " " + transcript
                            print(f"[DeepgramSTT] Final: '{transcript}'")
                        else:
                            print(f"[DeepgramSTT] Interim: '{transcript}'")
                        
                        # Call callback
                        if self.on_transcript:
                            asyncio.create_task(
                                self._async_callback(transcript, is_final)
                            )
        except Exception as e:
            print(f"[DeepgramSTT] Error handling message: {e}")
    
    async def stop(self):
        """Stop the STT connection"""
        self._is_listening = False
        if self.connection:
            try:
                await self.connection.close()
            except:
                pass
            self.connection = None
        if hasattr(self, '_connection_ctx'):
            try:
                await self._connection_ctx.__aexit__(None, None, None)
            except:
                pass
        print("[DeepgramSTT] Stopped")
    
    async def process_audio(self, audio_data: bytes):
        """
        Process audio chunk for transcription
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit, 16kHz, mono)
        """
        if self._is_listening and self.connection:
            try:
                await self.connection.send(audio_data)
            except Exception as e:
                print(f"[DeepgramSTT] Error sending audio: {e}")
    
    async def _async_callback(self, transcript: str, is_final: bool):
        """Async wrapper for callback"""
        if self.on_transcript:
            await self.on_transcript(transcript, is_final)
    
    def get_final_transcript(self) -> str:
        """Get accumulated final transcripts"""
        return self._final_buffer.strip()
    
    def clear_buffer(self):
        """Clear the transcript buffer"""
        self._final_buffer = ""
    
    def is_listening(self) -> bool:
        """Check if STT is active"""
        return self._is_listening


class MockSTTProcessor:
    """
    Mock STT processor for testing without Deepgram API
    """
    
    def __init__(self):
        self.on_transcript: Optional[Callable[[str, bool], None]] = None
        self._mock_transcripts = [
            "Hi, I'd like to order some wings",
            "What flavors do you have?",
            "I'll take 10 boneless with Lemon Pepper",
            "That's all",
        ]
        self._index = 0
    
    async def start(self):
        print("[MockSTT] Started (mock mode)")
        return True
    
    async def stop(self):
        print("[MockSTT] Stopped")
    
    async def process_audio(self, audio_data: bytes):
        """Mock audio processing - does nothing"""
        pass
    
    async def simulate_transcript(self, text: str = None):
        """Simulate receiving a transcript (for testing)"""
        if text is None:
            if self._index < len(self._mock_transcripts):
                text = self._mock_transcripts[self._index]
                self._index += 1
            else:
                text = "Thank you"
        
        print(f"[MockSTT] Simulated: '{text}'")
        if self.on_transcript:
            await self.on_transcript(text, True)
