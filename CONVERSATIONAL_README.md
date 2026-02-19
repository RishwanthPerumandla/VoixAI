# VoixAI Conversational - Wingstop Order Taking AI

A conversational AI agent for Wingstop ordering with a proper state machine that guides customers through a natural dialogue flow.

## Features

### Conversational State Machine
```
GREETING → ASKING_MAIN_ITEM → ASKING_FLAVOR/ASKING_COMBO → ASKING_DRINK → 
ASKING_SIDES → ASKING_DIP → CONFIRMING → COMPLETED
```

### Key Capabilities
- **Natural dialogue**: Asks one question at a time like a real cashier
- **Upsell logic**: Suggests combo for 6+ wings
- **Flavor management**: Handles multiple flavors with quantities
- **Order confirmation**: Repeats back before finalizing
- **Fast processing**: Uses `tiny.en` STT model for speed

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
set GROQ_API_KEY=your_key_here

# Run the conversational server
python main_conversational.py
```

Then open http://localhost:8000 in your browser.

## Example Conversation Flow

```
Tasha: "Hey! Welcome to Wingstop! I'm Tasha. How many wings can I get 
        started for you? Bone-in or boneless?"

User: "6 boneless"

Tasha: "6 boneless wings, nice choice! Want to make that a combo? Comes 
        with our famous seasoned fries and a drink, saves you about $3!"

User: "Sure, make it a combo"

Tasha: "Love it! What size drink? We got 20oz or 32oz."

User: "20oz Diet Coke"

Tasha: "Diet Coke, got it. And for the side - seasoned fries or veggie sticks?"

User: "Fries"

Tasha: "What dip you want with those fries? Ranch, blue cheese, or honey mustard?"

User: "Ranch"

Tasha: "Perfect! Now for those 6 boneless - what flavors are we feeling? 
        You can pick up to 2. Our Lemon Pepper is crazy popular!"

User: "3 Cajun and 3 lemon pepper"

Tasha: "3 Cajun, 3 Lemon Pepper - mixing it up, I like it! So that's 
        6 boneless combo with Cajun and Lemon Pepper, fries with ranch, 
        and a 20oz Diet Coke. Look right?"

User: "Yes"

Tasha: "Perfect! Pull up to the window!"
```

## Architecture

### Core Components

1. **ConversationalAgent** (`core/llm_agent_conversational.py`)
   - Manages dialogue state
   - Extracts order information
   - Handles upsell triggers
   - Generates contextual responses

2. **STT Engine** (`core/stt_engine.py`)
   - Uses `tiny.en` Whisper model for fastest transcription
   - Optimized for single-word and short phrase recognition

3. **TTS Engine** (`core/tts_engine_onnx.py`)
   - Kokoro ONNX for fast CPU synthesis
   - ~0.1-0.3s for typical responses

4. **Audio Processor** (in `main_conversational.py`)
   - VAD-based auto-detection of speech end
   - Low-latency processing pipeline

### State Definitions

| State | Purpose | Next State Trigger |
|-------|---------|-------------------|
| `GREETING` | Initial greeting | After user mentions wings |
| `ASKING_MAIN_ITEM` | Get wing qty & type | Wing qty > 0 |
| `ASKING_COMBO` | Upsell combo (6+ wings) | User responds yes/no |
| `ASKING_FLAVOR` | Get wing flavors | Flavors selected |
| `ASKING_DRINK` | Get drink & size | Drink specified |
| `ASKING_SIDES` | Get side choice | Side specified |
| `ASKING_DIP` | Get dip choice | Dip specified |
| `CONFIRMING` | Confirm order | User says yes/no |
| `COMPLETED` | Order done | - |

## Performance Optimizations

### For Speed
- **STT**: `tiny.en` model (~10x faster than `small.en`)
- **TTS**: Kokoro ONNX (pure CPU, no GPU needed)
- **LLM**: Groq with `llama-3.3-70b-versatile` (fast inference)
- **VAD**: Sensitive threshold (0.3) with 1.2s silence detection

### Typical Latency
- STT: 50-200ms
- LLM: 200-500ms
- TTS: 100-300ms
- **Total: 500ms - 1.5s**

## Wingstop Menu Support

### Flavors
- Lemon Pepper, Cajun, Garlic Parmesan
- Hickory Smoked BBQ, Mild, Original Hot
- Atomic, Mango Habanero
- Korean BBQ, Spicy Korean, Louisiana Rub

### Drinks
- Coke, Diet Coke, Sprite, Dr Pepper, Diet Dr Pepper
- Lemonade, Strawberry Lemonade, Mango Lemonade
- Iced Tea (Sweet/Unsweetened), Fruit Punch

### Sides
- Seasoned Fries, Veggie Sticks
- Cheese Fries, Buffalo Ranch Fries
- Cajun Corn, Coleslaw

### Dips
- Ranch, Blue Cheese, Honey Mustard
- Cheese Sauce, Teriyaki

## Environment Variables

```bash
GROQ_API_KEY=your_groq_api_key_here
```

## File Structure

```
VoixAI/
├── main_conversational.py          # Entry point
├── core/
│   └── llm_agent_conversational.py # Conversational state machine
├── static/
│   └── index_conversational.html   # UI
├── CONVERSATIONAL_README.md        # This file
└── config.yaml                     # Configuration
```
