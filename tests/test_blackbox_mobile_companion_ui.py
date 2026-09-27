"""Blackbox TDD frontdoor test suite for Spatial Companion Mobile UI (TASK-0134).

Governed by:
- ADR-0002: Event-Driven Watcher Architecture & Voice Audio
- ADR-0005: Kubernetes-First Infrastructure & Ingress Routing
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
import voice_agent.main as va_main
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.companion import mobile_companion_manager
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from voice_agent.main import app as voice_app

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_companion_ui_environment():
    """Ensure clean SpiceDB, Redis event bus, and companion connection state."""
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    va_main.set_event_bus(bus)
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()
    yield {"spicedb": mock_spicedb, "redis": mock_redis, "bus": bus}
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()
    va_main.set_event_bus(None)
    set_event_bus(None)
    set_spicedb_client(SpiceDBClient())


@pytest.fixture
def voice_client() -> TestClient:
    return TestClient(voice_app)


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & File Structure Integrity
# ---------------------------------------------------------------------------


def test_voice_agent_manifest_endpoint(voice_client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes runefoble-mobile-companion metadata."""
    resp = voice_client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "voice_agent"
    assert data["package"] == "@runefoble/voice-agent-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-mobile-companion" in data["components"]
    assert "runefoble-mobile-companion" in data["tags"]
    assert any("runefoble-mobile-companion.styles" in s for s in data["styles"])
    assert any("index.ts" in s for s in data["scripts"])


def test_manifest_file_matches_advertised_endpoint(voice_client: TestClient) -> None:
    """Verify services/voice_agent/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/voice_agent/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = voice_client.get("/ui/manifest").json()

    assert manifest_data["service"] == endpoint_data["service"]
    assert manifest_data["package"] == endpoint_data["package"]
    assert manifest_data["components"] == endpoint_data["components"]
    assert manifest_data["tags"] == endpoint_data["tags"]
    assert manifest_data["styles"] == endpoint_data["styles"]
    assert manifest_data["scripts"] == endpoint_data["scripts"]


def test_typescript_element_source_and_exports() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/voice_agent/ui"

    pkg_path = ui_dir / "package.json"
    assert pkg_path.is_file(), "package.json must exist"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    assert pkg["name"] == "@runefoble/voice-agent-ui"

    tsconfig_path = ui_dir / "tsconfig.json"
    assert tsconfig_path.is_file(), "tsconfig.json must exist"

    index_path = ui_dir / "src/index.ts"
    assert index_path.is_file(), "index.ts must exist"
    index_content = index_path.read_text(encoding="utf-8")
    assert "runefoble-mobile-companion" in index_content

    comp_path = ui_dir / "src/runefoble-mobile-companion.ts"
    assert comp_path.is_file(), "runefoble-mobile-companion.ts must exist"
    comp_code = comp_path.read_text(encoding="utf-8")
    assert "@customElement('runefoble-mobile-companion')" in comp_code
    assert "RunefobleMobileCompanion" in comp_code

    styles_path = ui_dir / "src/runefoble-mobile-companion.styles.ts"
    assert styles_path.is_file(), "runefoble-mobile-companion.styles.ts must exist"

    # App shell forwarding export
    shell_export = REPO_ROOT / "frontend/src/components/runefoble-mobile-companion.ts"
    assert shell_export.is_file(), (
        f"{shell_export} must exist for App Shell backwards compatibility"
    )
    assert "@runefoble/voice-agent-ui" in shell_export.read_text(encoding="utf-8")


def test_storybook_stories_coverage() -> None:
    """Verify Storybook stories include connection states, whisper vibrations, and interactive simulator."""
    stories_path = REPO_ROOT / "services/voice_agent/ui/src/runefoble-mobile-companion.stories.ts"
    assert stories_path.is_file(), "Storybook stories file must exist"
    content = stories_path.read_text(encoding="utf-8")

    assert "DefaultConnected" in content
    assert "SecretWhisperActive" in content
    assert "ConstrainedCellularFallback" in content
    assert "TurnAlertPrompt" in content
    assert "OfflineDisconnected" in content
    assert "InteractiveSimulator" in content


# ---------------------------------------------------------------------------
# 2. Component Behavioral Contracts & Capabilities
# ---------------------------------------------------------------------------


def test_component_haptic_and_webaudio_contracts() -> None:
    """Verify component implements haptic dispatcher, acoustic cues, and buffer monitor."""
    ui_src = REPO_ROOT / "services/voice_agent/ui/src"
    comp_file = ui_src / "runefoble-mobile-companion.ts"
    code = comp_file.read_text(encoding="utf-8")
    sub_code = "\n".join(
        f.read_text(encoding="utf-8") for f in (ui_src / "mobile_companion").glob("*.ts")
    )
    combined = code + "\n" + sub_code

    # Haptic feedback contract
    assert "triggerHaptic" in combined
    assert "navigator.vibrate" in combined
    assert "haptic-pulse" in combined

    # Acoustic cue contract (AudioContext synthesizer)
    assert "playAcousticCue" in combined
    assert "AudioContext" in combined
    assert "createOscillator" in combined

    # Diegetic secret whisper overlay & privacy blur
    assert "receiveWhisper" in combined
    assert "dismissWhisper" in combined
    assert "toggleWhisperBlur" in combined
    assert "whisper-received" in combined
    assert "whisper-dismissed" in combined
    assert "whisper-blur-toggled" in combined
    assert "isWhisperBlurred" in combined

    # Audio buffer monitor & adaptive sample rate indicator
    assert "bufferHealthMs" in combined
    assert "buffer-bar" in combined
    assert "bitrateKbps" in combined
    assert "packetLoss" in combined
    assert "sampleRate" in combined

    # Large thumb-friendly PTT button & channel indicator
    assert "handlePttStart" in combined
    assert "handlePttEnd" in combined
    assert "ptt-start" in combined
    assert "ptt-end" in combined
    assert "channelName" in combined

    # WebSocket dispatcher
    assert "handleWebSocketMessage" in combined
    assert "connectWebSocket" in combined
    assert "disconnectWebSocket" in combined


# ---------------------------------------------------------------------------
# 3. Gateway WebSocket & Haptic Protocol Frontdoor Integration
# ---------------------------------------------------------------------------


def test_gateway_websocket_frontdoor_handshake_and_frames(client: TestClient) -> None:
    """Verify WebSocket protocol delivers frames matching the component's dispatcher."""
    spicedb = get_spicedb_client()
    session_id, user_id = f"sess-{uuid4().hex[:6]}", "marcus"
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))

    with client.websocket_connect(
        f"/ws/mobile-companion/{session_id}?user_id={user_id}&peer_id=peer_marcus"
    ) as ws:
        # 1. Connected handshake frame consumed by mobile_companion_connected handler
        conn_frame = ws.receive_json()
        assert conn_frame["type"] == "mobile_companion_connected"
        assert conn_frame["session_id"] == session_id
        assert "audio_profile" in conn_frame
        assert conn_frame["audio_profile"]["sample_rate"] == 16000
        assert conn_frame["audio_profile"]["bitrate_kbps"] == 16

        # 2. Telemetry frame -> audio_profile_adapted frame
        ws.send_json(
            {
                "type": "mobile_telemetry",
                "packet_loss": 0.08,
                "bandwidth_kbps": 40.0,
                "latency_ms": 110.0,
            }
        )
        adapt_frame = ws.receive_json()
        assert adapt_frame["type"] == "audio_profile_adapted"
        assert adapt_frame["current_tier"] == "cellular_constrained"
        assert adapt_frame["profile"]["bitrate_kbps"] == 12

        # 3. Trigger haptic ping -> haptic_ping frame with vibration pattern
        ws.send_json(
            {
                "type": "trigger_haptic",
                "alert_type": "secret_whisper",
                "recipient_id": user_id,
            }
        )
        haptic_frame = ws.receive_json()
        assert haptic_frame["type"] == "haptic_ping"
        assert haptic_frame["alert_type"] == "secret_whisper"
        assert haptic_frame["vibration_pattern"] == [200, 100, 200]


def test_public_http_whisper_and_turn_alert_delivery(client: TestClient) -> None:
    """Verify HTTP whisper & turn alert endpoints deliver haptic frames to mobile client."""
    spicedb = get_spicedb_client()
    session_id, user_id = f"sess-{uuid4().hex[:6]}", "marcus"
    dm_user = "the_watcher_dm"
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))
    asyncio.run(
        spicedb.write_relationship("campaign", session_id, "dungeon_master", "user", dm_user)
    )

    with client.websocket_connect(
        f"/ws/mobile-companion/{session_id}?user_id={user_id}&peer_id=peer_marcus"
    ) as ws:
        _ = ws.receive_json()  # Consume connected frame

        # Dispatch secret whisper via public HTTP frontdoor
        whisper_res = client.post(
            f"/api/v1/mobile/companion/{session_id}/whisper",
            headers={"X-User-Id": dm_user},
            json={
                "recipient_id": user_id,
                "sender": "The Watcher",
                "content": "A hidden door clicks open behind the tapestry.",
                "character_name": "Marcus",
            },
        )
        assert whisper_res.status_code == 200
        whisper_frame = ws.receive_json()
        assert whisper_frame["type"] == "haptic_ping"
        assert whisper_frame["whisper"] is not None
        assert whisper_frame["whisper"]["sender"] == "The Watcher"
        assert "hidden door" in whisper_frame["whisper"]["content"]

        # Dispatch combat turn alert via public HTTP frontdoor
        alert_res = client.post(
            f"/api/v1/mobile/companion/{session_id}/turn-alert",
            headers={"X-User-Id": dm_user},
            json={"recipient_id": user_id, "character_name": "Marcus", "round_num": 2},
        )
        assert alert_res.status_code == 200
        turn_frame = ws.receive_json()
        assert turn_frame["type"] == "haptic_ping"
        assert turn_frame["alert_type"] == "turn_alert"
        assert turn_frame["notification"]["turn_alert"] is True
        assert turn_frame["vibration_pattern"] == [300, 150, 300]
