# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-02-17

### Added
- Initial release of VoixAI voice ordering system
- Real-time WebSocket communication for voice conversations
- Speech-to-Text using faster-whisper (tiny.en)
- Integration with Groq API for LLM reasoning (llama-3.3-70b-versatile)
- Text-to-Speech using Kokoro TTS engine
- Voice Activity Detection using Silero VAD
- Function calling for structured order extraction
- SQLite persistence for orders and conversation logs
- Tasha persona: casual speech patterns ("lemme", "gonna")
- Web-based client with push-to-talk interface
- Latency monitoring and logging
- Configuration via YAML file

### Technical Details
- CPU-only operation (no GPU required)
- Sample rate: 16kHz PCM input, 24kHz output
- STT compute type: int8 for speed
- Maximum response length: 12 words
- Conversation state machine: GREETING -> TAKING_ITEMS -> CONFIRMING -> CLOSING

### Known Issues
- TTS generation is slow on CPU (2-5 seconds)
- Limited to single-session WebSocket connections
- No multi-language support
- Order extraction may confuse similar items

## Future Roadmap

### [1.1.0] Planned
- GPU support for faster TTS
- Multiple concurrent sessions
- Order modification during confirmation
- Better error recovery

### [1.2.0] Planned
- Phone integration (Twilio)
- Multi-language support (Spanish)
- Admin dashboard for order monitoring
- Export orders to POS systems

### [2.0.0] Planned
- Streaming TTS for lower latency
- Custom voice training
- A/B testing for personas
- Analytics and reporting
