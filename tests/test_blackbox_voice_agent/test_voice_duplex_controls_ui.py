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
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from voice_agent.main import app as voice_app
from voice_agent.main import set_event_bus

from tests.helpers.audio_synth import generate_pcm_sine

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


def test_duplex_controls_modular_file_limits() -> None:
    """Verify Hard Invariant 6 & DoD file limits (<180 for component, <140 for panel, <110 for styles)."""
    limits = {
        "services/voice_agent/ui/src/runefoble-voice-duplex-controls.ts": 180,
        "services/voice_agent/ui/src/duplex/settings_panel.ts": 140,
        "services/voice_agent/ui/src/duplex/styles/meters.styles.ts": 110,
        "services/voice_agent/ui/src/duplex/styles/controls.styles.ts": 110,
        "services/voice_agent/ui/src/duplex/styles/settings.styles.ts": 110,
        "services/voice_agent/ui/src/duplex/styles/index.ts": 30,
        "services/voice_agent/ui/src/runefoble-voice-duplex-controls.stories.ts": 180,
        "tests/test_blackbox_voice_agent/test_voice_duplex_controls_ui.py": 190,
    }
    for rel_path, max_lines in limits.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"{full_path} must exist"
        lines = len(full_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{rel_path} has {lines} lines, exceeding target {max_lines}"
        assert lines < 190, f"{rel_path} has {lines} lines, exceeding strict DoD limit 190"


def test_duplex_controls_component_contracts() -> None:
    """Verify component and panel contracts, custom elements, and events."""
    ui_src = REPO_ROOT / "services/voice_agent/ui/src"
    comp_code = (ui_src / "runefoble-voice-duplex-controls.ts").read_text(encoding="utf-8")
    panel_code = (ui_src / "duplex/settings_panel.ts").read_text(encoding="utf-8")
    index_code = (ui_src / "index.ts").read_text(encoding="utf-8")

    assert "@customElement('runefoble-voice-duplex-controls')" in comp_code
    assert "@customElement('duplex-settings-panel')" in panel_code
    assert "runefoble-voice-duplex-controls" in index_code
    assert "duplex-settings-panel" in index_code or "settings_panel" in index_code

    # Event dispatches
    assert "duplex-interrupted" in comp_code
    assert "vad-sensitivity-change" in panel_code
    assert "ducking-gain-change" in panel_code
    assert "aec-toggle" in panel_code

    # Public control methods
    assert "triggerBargeIn" in comp_code
    assert "resetBargeIn" in comp_code
    assert "toggleSettings" in comp_code
    assert "handleWebSocketMessage" in comp_code


def test_duplex_storybook_stories_coverage() -> None:
    """Verify interactive Storybook stories cover all visual duplex states."""
    stories_path = (
        REPO_ROOT / "services/voice_agent/ui/src/runefoble-voice-duplex-controls.stories.ts"
    )
    assert stories_path.is_file()
    content = stories_path.read_text(encoding="utf-8")
    for story in [
        "IdleStandby",
        "PlaybackActive",
        "PlayerBargeInInterjection",
        "DmMutedWithCrossfade",
        "VADCalibrationSettings",
        "InteractiveSimulator",
    ]:
        assert story in content, f"Story {story} missing from stories file"


def test_app_shell_forwarding_export() -> None:
    """Verify App Shell forwarding export for runefoble-voice-duplex-controls."""
    shell_file = REPO_ROOT / "frontend/src/components/runefoble-voice-duplex-controls.ts"
    assert shell_file.is_file()
    assert "@runefoble/voice-agent-ui" in shell_file.read_text(encoding="utf-8")


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
