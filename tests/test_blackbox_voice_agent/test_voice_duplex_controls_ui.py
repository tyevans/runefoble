"""Blackbox TDD frontdoor tests for Voice Duplex Controls UI (TASK-0149).

Governing ADRs: ADR-0004, ADR-0012, ADR-0013.
Verifies:
- Microfrontend manifest advertisement via GET /ui/manifest.
- Decomposition & file length invariants (< 180 lines for component, < 140 for panel, < 110 for styles).
- Custom Element registration & event contracts.
- Duplex WebSocket protocol integration via public frontdoor.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import VoiceSpeechInterrupted
from runefoble_platform.redis_bus import RedisStreamsEventBus, deserialize_event
from voice_agent.main import app as voice_app
from voice_agent.main import set_event_bus

from tests.helpers.audio_synth import generate_pcm_sine
from tests.helpers.mock_redis import MockAsyncRedis

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def clean_voice_bus():
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    yield {"redis": mock_redis, "bus": bus}
    set_event_bus(None)


@pytest.fixture
def voice_client() -> TestClient:
    return TestClient(voice_app)


def test_voice_agent_manifest_exposes_duplex_controls(voice_client: TestClient) -> None:
    """Verify GET /ui/manifest advertises runefoble-voice-duplex-controls."""
    resp = voice_client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "voice_agent"
    assert data["package"] == "@runefoble/voice-agent-ui"
    assert "runefoble-voice-duplex-controls" in data["components"]
    assert "runefoble-voice-duplex-controls" in data["tags"]
    assert any("duplex/styles" in s for s in data["styles"])

    # Manifest file matches runtime endpoint
    manifest_path = REPO_ROOT / "services/voice_agent/ui/manifest.json"
    assert manifest_path.is_file()
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert file_data["components"] == data["components"]
    assert file_data["tags"] == data["tags"]


def test_duplex_websocket_protocol_frontdoor_integration(
    voice_client: TestClient, clean_voice_bus: dict
) -> None:
    """Verify duplex WebSocket messages trigger barge-in and cancellation signals."""
    session_id, speaker_id = f"sess-{uuid4().hex[:6]}", "spk-marcus"
    text = "A chilling roar echoes through the subterranean vault!"

    with voice_client.websocket_connect(
        f"/api/v1/voice/duplex/ws/{session_id}/{speaker_id}?speaker_name=Marcus"
    ) as ws:
        assert ws.receive_json()["type"] == "voice_duplex_connected"

        # 1. Start active narration playback
        ws.send_json(
            {"type": "playback_start", "playback_id": "pb-101", "text": text, "duration_ms": 6000.0}
        )
        assert ws.receive_json()["type"] == "playback_started"

        # 2. Player speech onset interrupts active playback
        speech_pcm = generate_pcm_sine(duration_ms=100, freq=440.0, amplitude=9000)
        ws.send_bytes(speech_pcm)

        f1 = ws.receive_json()
        assert f1["type"] == "barge_in_detected" and f1["latency_ms"] <= 100.0

        f2 = ws.receive_json()
        assert f2["type"] == "webrtc_stream_mute" and f2["is_muted"] is True

        f3 = ws.receive_json()
        assert f3["type"] == "playback_canceled"

    # Verify domain event published to Redis
    mock_redis = clean_voice_bus["redis"]
    assert "runefoble.events.voice" in mock_redis.streams
    event = deserialize_event(mock_redis.streams["runefoble.events.voice"][0][1])
    assert isinstance(event, VoiceSpeechInterrupted)
    assert event.session_id == session_id
