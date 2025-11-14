from gtts import gTTS
import io
from utils.logger import log
from utils.timer import measure

def synthesize_text(text: str):
    step = measure("TTS: gTTS internal")

    log(f"🗣️ Generating TTS response: {text}")

    tts = gTTS(text=text, lang="en", slow=False)
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)

    step()
    return audio_buffer
