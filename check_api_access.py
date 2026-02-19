"""Check if OpenAI Realtime API is available"""
import os
from dotenv import load_dotenv
load_dotenv()

import urllib.request
import json

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("[X] OPENAI_API_KEY not set")
    exit(1)

print("Checking OpenAI API access...")
print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
print()

req = urllib.request.Request(
    'https://api.openai.com/v1/models',
    headers={'Authorization': f'Bearer {api_key}'}
)

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
        models = [m.get('id', '') for m in data.get('data', [])]
        
        print(f"Total models available: {len(models)}")
        print()
        
        realtime_models = [m for m in models if 'realtime' in m]
        if realtime_models:
            print("[OK] Realtime API is AVAILABLE!")
            print("Models:")
            for m in realtime_models:
                print(f"  - {m}")
        else:
            print("[WARNING] No realtime models found")
            print("Your account may not have Realtime API access yet.")
            print()
            print("Available GPT-4 models:")
            for m in sorted(models):
                if 'gpt-4' in m:
                    print(f"  - {m}")
                    
except urllib.error.HTTPError as e:
    print(f"[X] API Error: HTTP {e.code}")
    print(f"  {e.reason}")
except Exception as e:
    print(f"[X] Error: {e}")
