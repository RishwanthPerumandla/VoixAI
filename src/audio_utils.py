"""
Audio Utilities for VoixAI
"""

import io


def convert_audio_to_pcm(audio_bytes: bytes, source_format: str = "webm") -> bytes:
    """
    Convert audio to 16kHz 16-bit PCM mono format for Deepgram
    """
    try:
        from pydub import AudioSegment
        
        # Load audio from bytes (auto-detect format)
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=source_format)
        
        print(f"[AudioUtils] Input: {audio.frame_rate}Hz, {audio.sample_width*8}-bit, {audio.channels}ch")
        
        # Convert to mono
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Convert to 16kHz
        if audio.frame_rate != 16000:
            audio = audio.set_frame_rate(16000)
        
        # Convert to 16-bit
        if audio.sample_width != 2:
            audio = audio.set_sample_width(2)
        
        pcm_data = audio.raw_data
        print(f"[AudioUtils] Output: 16000Hz, 16-bit, mono, {len(pcm_data)} bytes")
        
        return pcm_data
        
    except Exception as e:
        print(f"[AudioUtils] Error: {e}")
        return audio_bytes
