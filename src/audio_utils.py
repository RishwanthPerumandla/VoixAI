"""
Audio Utilities for VoixAI
Handles audio format conversion using pydub
"""

import io
import wave
import struct


def convert_audio_to_pcm(audio_bytes: bytes, source_format: str = "wav") -> bytes:
    """
    Convert audio to 16kHz 16-bit PCM mono format for Deepgram
    
    Args:
        audio_bytes: Raw audio bytes
        source_format: Source format (wav, webm, etc.)
    
    Returns:
        PCM audio bytes (16kHz, 16-bit, mono)
    """
    try:
        # Try using pydub first
        from pydub import AudioSegment
        
        # Load audio from bytes
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        
        print(f"[AudioUtils] Input: {audio.frame_rate}Hz, {audio.sample_width*8}-bit, {audio.channels}ch, {len(audio)}ms")
        
        # Convert to mono
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Convert to 16kHz
        if audio.frame_rate != 16000:
            audio = audio.set_frame_rate(16000)
        
        # Convert to 16-bit
        if audio.sample_width != 2:
            audio = audio.set_sample_width(2)
        
        # Export as raw PCM
        pcm_data = audio.raw_data
        
        print(f"[AudioUtils] Output PCM: 16000Hz, 16-bit, mono, {len(pcm_data)} bytes")
        
        return pcm_data
        
    except Exception as e:
        print(f"[AudioUtils] pydub error: {e}, trying fallback...")
        return convert_wav_to_pcm_fallback(audio_bytes)


def convert_wav_to_pcm_fallback(wav_bytes: bytes) -> bytes:
    """
    Fallback WAV to PCM conversion using wave module
    """
    try:
        wav_file = wave.open(io.BytesIO(wav_bytes), 'rb')
        
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        print(f"[AudioUtils] Fallback WAV: {frame_rate}Hz, {sample_width*8}-bit, {n_channels}ch")
        
        raw_data = wav_file.readframes(n_frames)
        wav_file.close()
        
        return raw_data
        
    except Exception as e:
        print(f"[AudioUtils] Fallback error: {e}")
        return wav_bytes


def create_wav_header(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """
    Create WAV header for PCM data
    """
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    data_size = len(pcm_data)
    
    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        sample_width * 8,
        b'data',
        data_size
    )
    
    return wav_header + pcm_data
