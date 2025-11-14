from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from services.stt_service import transcribe_audio
from services.tts_service import synthesize_text
from utils.timer import measure

router = APIRouter()

@router.post("/process")
async def process_audio(file: UploadFile = File(...)):
    total = measure("🚀 TOTAL request time")

    t0 = measure("📥 File read")
    audio_bytes = await file.read()
    t0()

    t1 = measure("🧠 STT (Whisper)")
    text = transcribe_audio(audio_bytes)
    t1()

    t2 = measure("🔊 TTS (gTTS)")
    audio_buffer = synthesize_text(f"You said: {text}")
    t2()

    total()

    return StreamingResponse(audio_buffer, media_type="audio/wav")
