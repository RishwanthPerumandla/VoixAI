"""
Deepgram Speech-to-Text Processor - Real Implementation
Real-time streaming transcription using Deepgram Nova 2
"""

import asyncio
import json
from typing import Callable, Optional
from deepgram import Deepgram

from src.config import settings


class DeepgramSTTProcessor:
    """
    Speech-to-Text processor using Deepgram Nova 2
    
    Features:
    - Streaming transcription
    - Interim and final results
    - Low latency (<300ms)
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.deepgram_api_key
        self.dg_client = Deepgram(self.api_key)
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
            # Deepgram SDK v2 uses transcription.live
            self.connection = await self.dg_client.transcription.live(
                {
                    "smart_format": True,
                    "interim_results": True,
                    "language": "en-US",
                    "model": "nova-2",
                    "punctuate": True,
                    "endpointing": 300,
                }
            )
            
            # Register event handlers
            self.connection.registerHandler(
                self.connection.event.CLOSE,
                lambda _: self._handle_close()
            )
            
            self.connection.registerHandler(
                self.connection.event.TRANSCRIPT_RECEIVED,
                self._handle_transcript
            )
            
            self._is_listening = True
            print("[DeepgramSTT] Started listening")
            return True
                
        except Exception as e:
            print(f"[DeepgramSTT] Error starting: {e}")
            if self.on_error:
                await self.on_error(e)
            return False
    
    async def stop(self):
        """Stop the STT connection"""
        self._is_listening = False
        if self.connection:
            try:
                self.connection.finish()
            except:
                pass
            self.connection = None
        print("[DeepgramSTT] Stopped")
    
    async def process_audio(self, audio_data: bytes):
        """
        Process audio chunk for transcription
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit, 16kHz, mono)
        """
        if self._is_listening and self.connection:
            try:
                self.connection.send(audio_data)
            except Exception as e:
                print(f"[DeepgramSTT] Error sending audio: {e}")
    
    def _handle_transcript(self, result):
        """Handle transcript from Deepgram"""
        try:
            # Parse result
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result
            
            # Extract transcript
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [])
            
            if alternatives:
                transcript = alternatives[0].get("transcript", "")
                is_final = data.get("is_final", False)
                
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
            print(f"[DeepgramSTT] Error handling transcript: {e}")
    
    async def _async_callback(self, transcript: str, is_final: bool):
        """Async wrapper for callback"""
        if self.on_transcript:
            await self.on_transcript(transcript, is_final)
    
    def _handle_close(self):
        """Handle connection close"""
        print("[DeepgramSTT] Connection closed")
        self._is_listening = False
    
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
