"""Audio Stream Buffer with VAD detection"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
import torch
from typing import Optional


def normalize_audio(audio: np.ndarray, target_rms: float = 0.1, 
                   noise_gate: float = 0.01) -> np.ndarray:
    """
    Normalize audio to target RMS level.
    
    Args:
        audio: Input audio array
        target_rms: Target RMS level (0.1 = -20dB)
        noise_gate: Minimum level to avoid amplifying silence
    
    Returns:
        Normalized audio array
    """
    # Calculate current RMS
    rms = np.sqrt(np.mean(audio ** 2))
    
    # If below noise gate, don't amplify (it's probably silence)
    if rms < noise_gate:
        return audio
    
    # Calculate gain needed
    gain = target_rms / (rms + 1e-8)
    
    # Limit gain to avoid clipping (max 20x amplification)
    gain = min(gain, 20.0)
    
    # Apply gain
    normalized = audio * gain
    
    # Soft clipping to prevent hard distortion
    normalized = np.tanh(normalized)
    
    return normalized


class AudioBuffer:
    """Accumulates audio chunks and detects end of utterance using Silero VAD"""
    
    def __init__(self, sample_rate: int = 16000, silence_ms: int = 1500, 
                 vad_threshold: float = 0.4, min_utterance_ms: int = 800,
                 normalization: bool = True, noise_gate: float = 0.01):
        self.sample_rate = sample_rate
        self.silence_samples = int(silence_ms * sample_rate / 1000)
        self.min_utterance_samples = int(min_utterance_ms * sample_rate / 1000)
        self.vad_threshold = vad_threshold
        self.normalization = normalization
        self.noise_gate = noise_gate
        
        # Load Silero VAD
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        self.model.eval()
        
        # State
        self.buffer = np.array([], dtype=np.float32)
        self.silence_counter = 0
        self.is_speaking = False
        
    def add_chunk(self, chunk_bytes: bytes) -> Optional[np.ndarray]:
        """
        Add a chunk of audio bytes (Int16) to the buffer.
        Returns complete utterance if silence detected, else None.
        """
        # Convert Int16 bytes to float32 [-1, 1]
        chunk_int16 = np.frombuffer(chunk_bytes, dtype=np.int16)
        chunk_float32 = chunk_int16.astype(np.float32) / 32768.0
        
        # Apply normalization if enabled
        if self.normalization:
            chunk_float32 = normalize_audio(chunk_float32, 
                                          target_rms=0.1, 
                                          noise_gate=self.noise_gate)
        
        # Append to buffer
        self.buffer = np.concatenate([self.buffer, chunk_float32])
        
        # Run VAD on latest chunk (get speech probability)
        # VAD expects tensor of shape (batch, samples)
        chunk_tensor = torch.from_numpy(chunk_float32).unsqueeze(0)
        
        with torch.no_grad():
            try:
                speech_prob = self.model(chunk_tensor, self.sample_rate).item()
            except Exception:
                # Fallback: use simple energy-based detection
                speech_prob = np.abs(chunk_float32).mean() * 2  # Rough estimate
        
        # Debug logging (every 20 chunks)
        debug = len(self.buffer) % (4096 * 20) < 4096
        if debug:
            buffer_sec = len(self.buffer)/16000
            rms = np.sqrt(np.mean(chunk_float32**2))
            print(f"[VAD] prob={speech_prob:.2f}, speaking={self.is_speaking}, silence={self.silence_counter/16000:.2f}s, buf={buffer_sec:.2f}s, rms={rms:.4f}")
        
        # State machine for voice activity
        if speech_prob > self.vad_threshold:
            if not self.is_speaking and debug:
                print(f"[VAD] Speech started!")
            self.is_speaking = True
            self.silence_counter = 0
        else:
            if self.is_speaking:
                self.silence_counter += len(chunk_float32)
                if debug:
                    print(f"[VAD] Silence: {self.silence_counter/16000:.2f}s / {self.silence_samples/16000:.2f}s")
            
            # Check if silence duration exceeded
            if self.silence_counter >= self.silence_samples:
                buffer_sec = len(self.buffer) / self.sample_rate
                print(f"[VAD] Silence threshold reached! Buffer: {buffer_sec:.2f}s, is_speaking was: {self.is_speaking}")
                # End of utterance detected
                if len(self.buffer) >= self.min_utterance_samples:
                    utterance = self.buffer.copy()
                    
                    # Final normalization of full utterance
                    if self.normalization:
                        utterance = normalize_audio(utterance, target_rms=0.15, noise_gate=0.005)
                    
                    self.reset()
                    return utterance
                else:
                    print(f"[VAD] Utterance too short ({buffer_sec:.2f}s < {self.min_utterance_samples/self.sample_rate:.2f}s), resetting")
                    self.reset()
                    
        return None
    
    def reset(self):
        """Clear the internal audio buffer"""
        self.buffer = np.array([], dtype=np.float32)
        self.silence_counter = 0
        self.is_speaking = False
