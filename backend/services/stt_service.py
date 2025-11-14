from faster_whisper import WhisperModel
from utils.logger import log
from utils.timer import measure
import io

log("🔊 Loading Faster-Whisper...")
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")

def transcribe_audio(audio_bytes: bytes):
    step = measure("STT: Transcription internal")

    log("🎧 Transcribing audio...")
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "input.wav"

    segments, info = model.transcribe(
        audio_file,
        beam_size=1,
        best_of=1,
        vad_filter=True,
        without_timestamps=True
    )

    text = "".join([s.text for s in segments])
    log(f"📝 Transcribed: {text}")

    step()
    return text
