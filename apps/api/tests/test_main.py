import json
from pathlib import Path

import pytest

import main as api_main


def test_session_config_path_sanitizes_room_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_main, "SESSION_CONFIG_DIR", tmp_path)

    path = api_main._session_config_path("room name/with spaces")

    assert path == tmp_path / "room-name-with-spaces.json"


@pytest.mark.asyncio
async def test_create_livekit_token_persists_runtime_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_main, "SESSION_CONFIG_DIR", tmp_path)
    monkeypatch.setattr(api_main, "LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setattr(api_main, "LIVEKIT_API_KEY", "lk-key")
    monkeypatch.setattr(api_main, "LIVEKIT_API_SECRET", "lk-secret")
    monkeypatch.setattr(api_main, "AGENT_NAME", "test-agent")

    class FakeAccessToken:
        def __init__(self, api_key: str, api_secret: str) -> None:
            assert api_key == "lk-key"
            assert api_secret == "lk-secret"
            self.identity = None
            self.name = None
            self.grants = None
            self.room_config = None

        def with_identity(self, identity: str):
            self.identity = identity
            return self

        def with_name(self, name: str):
            self.name = name
            return self

        def with_grants(self, grants):
            self.grants = grants
            return self

        def with_room_config(self, room_config):
            self.room_config = room_config
            return self

        def to_jwt(self) -> str:
            return "fake-jwt-token"

    monkeypatch.setattr(api_main, "AccessToken", FakeAccessToken)

    payload = api_main.TokenRequest(
        room_name="voixai-demo-room",
        participant_name="web-user",
        runtime_config={
            "scenario_id": "wingstop_inbound_ordering",
            "channel_id": "web",
            "voice_engine": "gemini_live",
            "preset_id": "gemini-live-voice",
        },
    )

    response = await api_main.create_livekit_token(payload)

    assert response.livekit_url == "wss://example.livekit.cloud"
    assert response.token == "fake-jwt-token"
    assert response.room_name == "voixai-demo-room"

    config_path = tmp_path / "voixai-demo-room.json"
    assert config_path.exists()
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "scenario_id": "wingstop_inbound_ordering",
        "channel_id": "web",
        "voice_engine": "gemini_live",
        "preset_id": "gemini-live-voice",
    }
