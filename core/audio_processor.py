"""Multi-core audio processing using ProcessPoolExecutor"""
import os
import asyncio
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import time

# Global variables for worker processes (initialized once per process)
_stt_engine = None
_tts_engine = None


def init_worker(stt_config, tts_config):
    """Initialize engines in worker process (called once per process)"""
    global _stt_engine, _tts_engine
    
    # Suppress torch warnings in workers
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    
    # Import here to avoid pickling issues
    from core.stt_engine import STTEngine
    from core.tts_engine_onnx import TTSEngineONNX
    
    print(f"[Worker {os.getpid()}] Initializing STT...")
    _stt_engine = STTEngine(
        model_size=stt_config["model"],
        device="cpu",
        compute_type=stt_config.get("compute_type", "int8"),
        language=stt_config.get("language", "en")
    )
    
    print(f"[Worker {os.getpid()}] Initializing TTS...")
    _tts_engine = TTSEngineONNX(
        voice=tts_config.get("voice", "af_bella"),
        speed=tts_config.get("speed", 1.0)
    )
    
    print(f"[Worker {os.getpid()}] Ready")


def process_stt(audio_bytes: bytes) -> str:
    """Run STT in worker process"""
    global _stt_engine
    audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
    return _stt_engine.transcribe(audio_array)


def process_tts(text: str) -> bytes:
    """Run TTS in worker process"""
    global _tts_engine
    return _tts_engine.synthesize(text)


class MultiCoreAudioProcessor:
    """Manages process pool for parallel audio processing"""
    
    def __init__(self, stt_config: dict, tts_config: dict, max_workers: int = None):
        """
        Args:
            max_workers: Number of worker processes. 
                        Default: min(4, CPU count) for quad-core CPU
        """
        if max_workers is None:
            # Leave 1 core free for main process and system
            max_workers = min(4, max(1, os.cpu_count() - 1))
        
        self.max_workers = max_workers
        self.stt_config = stt_config
        self.tts_config = tts_config
        self.executor = None
        
        print(f"[AudioProcessor] Creating pool with {max_workers} workers")
    
    async def start(self):
        """Start the process pool"""
        self.executor = ProcessPoolExecutor(
            max_workers=self.max_workers,
            initializer=init_worker,
            initargs=(self.stt_config, self.tts_config)
        )
        
        # Warm up workers with a dummy task
        loop = asyncio.get_event_loop()
        warmup_tasks = [
            loop.run_in_executor(self.executor, process_stt, np.zeros(16000, dtype=np.float32).tobytes())
            for _ in range(self.max_workers)
        ]
        await asyncio.gather(*warmup_tasks, return_exceptions=True)
        print("[AudioProcessor] Workers warmed up")
    
    async def stop(self):
        """Shutdown the process pool"""
        if self.executor:
            self.executor.shutdown(wait=True)
            print("[AudioProcessor] Shutdown complete")
    
    async def transcribe(self, audio_array: np.ndarray) -> str:
        """Async wrapper for STT processing"""
        loop = asyncio.get_event_loop()
        start = time.time()
        
        # Convert to bytes for pickling
        audio_bytes = audio_array.astype(np.float32).tobytes()
        
        # Run in process pool (non-blocking)
        result = await loop.run_in_executor(
            self.executor,
            process_stt,
            audio_bytes
        )
        
        elapsed = time.time() - start
        print(f"[AudioProcessor] STT took {elapsed:.2f}s")
        return result
    
    async def synthesize(self, text: str) -> bytes:
        """Async wrapper for TTS processing"""
        loop = asyncio.get_event_loop()
        start = time.time()
        
        # Run in process pool (non-blocking)
        result = await loop.run_in_executor(
            self.executor,
            process_tts,
            text
        )
        
        elapsed = time.time() - start
        print(f"[AudioProcessor] TTS took {elapsed:.2f}s")
        return result


# Singleton instance
_processor = None


async def get_processor(stt_config=None, tts_config=None) -> MultiCoreAudioProcessor:
    """Get or create the global processor instance"""
    global _processor
    if _processor is None and stt_config is not None:
        _processor = MultiCoreAudioProcessor(stt_config, tts_config)
        await _processor.start()
    return _processor


async def shutdown_processor():
    """Shutdown the global processor"""
    global _processor
    if _processor:
        await _processor.stop()
        _processor = None
