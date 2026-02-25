"""
Deepgram Speech-to-Text Processor
Real-time streaming transcription using Deepgram Nova 2
"""

import asyncio
import json
from typing import Callable, Optional

from src.config import settings

# Try to import Deepgram SDK v6
try:
    from deepgram import AsyncDeepgramClient, LiveTranscriptionEvents, LiveOptions
    DEEPGRAM_SDK_V6 = True
except ImportError:
    DEEPGRAM_SDK_V6 = False
    AsyncDeepgramClient = None
    LiveTranscriptionEvents = None
    LiveOptions = None


class DeepgramSTTProcessor:
    """
    Speech-to-Text processor using Deepgram Nova 2
    
    Features:
    - Streaming transcription
    - Interim and final results
    - Low latency (<300ms)
    """
    
    def __init__(self, api_key: str = None):
        if not DEEPGRAM_SDK_V6:
            raise ImportError("Deepgram SDK v6 not installed")
        
        self.api_key = api_key or settings.deepgram_api_key
        self.client = AsyncDeepgramClient(self.api_key)
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
            # Configure live transcription options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                interim_results=True,
                endpointing=300,
                punctuate=True,
                profanity_filter=False,
            )
            
            # Create connection using async client
            self.connection = await self.client.listen.asynclive.v("1")
            
            # Register event handlers
            self.connection.on(LiveTranscriptionEvents.Transcript, self._handle_transcript)
            self.connection.on(LiveTranscriptionEvents.Error, self._handle_error)
            self.connection.on(LiveTranscriptionEvents.Close, self._handle_close)
            
            # Start connection
            await self.connection.start(options)
            
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
                await self.connection.finish()
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
                await self.connection.send(audio_data)
            except Exception as e:
                print(f"[DeepgramSTT] Error sending audio: {e}")
    
    def _handle_transcript(self, result, **kwargs):
        """Handle transcript from Deepgram"""
        try:
            # Get the transcript
            transcript = result.channel.alternatives[0].transcript
            is_final = result.is_final
            
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
    
    def _handle_error(self, error, **kwargs):
        """Handle errors from Deepgram"""
        print(f"[DeepgramSTT] Error: {error}")
        if self.on_error:
            asyncio.create_task(self._async_error(error))
    
    async def _async_error(self, error):
        """Async wrapper for error callback"""
        if self.on_error:
            await self.on_error(error)
    
    def _handle_close(self, **kwargs):
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
