"""
Test script for voice APIs - Deepgram and Cartesia
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings


async def test_deepgram():
    """Test Deepgram STT API"""
    print("\n" + "="*60)
    print("Testing Deepgram STT API")
    print("="*60)
    
    if not settings.deepgram_api_key:
        print("[SKIP] No Deepgram API key found")
        return False
    
    try:
        from deepgram import Deepgram
        
        dg = Deepgram(settings.deepgram_api_key)
        
        # Try to create a transcription connection
        conn = await dg.transcription.live({
            "smart_format": True,
            "interim_results": True,
            "language": "en-US",
            "model": "nova-2",
        })
        
        print("[OK] Deepgram connection created successfully")
        
        # Close connection
        conn.finish()
        print("[OK] Deepgram connection closed")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Deepgram test failed: {e}")
        return False


async def test_cartesia():
    """Test Cartesia TTS API"""
    print("\n" + "="*60)
    print("Testing Cartesia TTS API")
    print("="*60)
    
    if not settings.cartesia_api_key:
        print("[SKIP] No Cartesia API key found")
        return False
    
    try:
        from cartesia import Cartesia
        
        client = Cartesia(api_key=settings.cartesia_api_key)
        
        # List available voices
        voices = client.voices.list()
        print(f"[OK] Cartesia connected. Available voices: {len(voices)}")
        
        # Try a simple synthesis
        test_text = "Hello, this is a test."
        chunks = []
        
        for chunk in client.tts.sse(
            model_id="sonic-english",
            transcript=test_text,
            voice_id="c2ac25f9-ecc4-4f56-909e-6c5bdd3a40da",
            stream=True,
            output_format={
                "container": "raw",
                "encoding": "pcm_f32le",
                "sample_rate": 24000,
            },
        ):
            audio = chunk.get("audio", b"")
            if audio:
                chunks.append(audio)
        
        total_bytes = sum(len(c) if isinstance(c, bytes) else len(c.encode()) for c in chunks)
        print(f"[OK] Cartesia synthesis successful: {total_bytes} bytes generated")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Cartesia test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_daily():
    """Test Daily.co API"""
    print("\n" + "="*60)
    print("Testing Daily.co API")
    print("="*60)
    
    if not settings.daily_api_key:
        print("[SKIP] No Daily.co API key found")
        return False
    
    try:
        import aiohttp
        
        url = "https://api.daily.co/v1/rooms"
        headers = {
            "Authorization": f"Bearer {settings.daily_api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"[OK] Daily.co API working. Rooms: {len(data.get('data', []))}")
                    return True
                else:
                    error = await resp.text()
                    print(f"[ERROR] Daily.co API error: {resp.status} - {error}")
                    return False
                    
    except Exception as e:
        print(f"[ERROR] Daily.co test failed: {e}")
        return False


async def main():
    """Run all API tests"""
    print("="*60)
    print("VoixAI v3.0 - Voice API Tests")
    print("="*60)
    
    results = {
        "Deepgram STT": await test_deepgram(),
        "Cartesia TTS": await test_cartesia(),
        "Daily.co": await test_daily(),
    }
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL/SKIP]"
        print(f"{status} {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n[SUCCESS] All voice APIs are working!")
    else:
        print("\n[WARNING] Some APIs failed or were skipped.")
        print("The server will use mock mode for failed APIs.")
    
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
