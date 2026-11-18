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

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from voice_agent.companion_registry import mobile_companion_manager
from voice_agent.main import app as voice_app

from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")
REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_companion_ui_environment(default_redis_event_bus, mock_bus):
    """Ensure clean SpiceDB, Redis event bus, and companion connection state."""
    mock_spicedb = get_spicedb_client()
    bus = default_redis_event_bus
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()
    yield {"spicedb": mock_spicedb, "redis": mock_bus, "bus": bus}
    mobile_companion_manager.active_companions.clear()
    mobile_companion_manager.peer_sessions.clear()
    mobile_companion_manager.active_profiles.clear()


@pytest.fixture
def voice_client() -> TestClient:
    return TestClient(voice_app)


@pytest.fixture
def client(gateway) -> TestClient:
    return gateway


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


# ---------------------------------------------------------------------------
# 2. Component Behavioral Contracts & Capabilities
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Gateway WebSocket & Haptic Protocol Frontdoor Integration
# ---------------------------------------------------------------------------


def test_gateway_websocket_frontdoor_handshake_and_frames(client: TestClient, table_for) -> None:
    """Verify WebSocket protocol delivers frames matching the component's dispatcher."""
    user_id = "marcus"
    _, session_id = table_for("the_watcher_dm", {user_id: "player"})

    with client.websocket_connect(
        f"/ws/mobile-companion/{session_id}?peer_id=peer_marcus",
        subprotocols=ws_subprotocols(user_id),
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


def test_public_http_whisper_and_turn_alert_delivery(
    client: TestClient, trusted_ws_issuer, table_for
) -> None:
    """Verify HTTP whisper & turn alert endpoints deliver haptic frames to mobile client."""
    user_id, dm_user = "marcus", "the_watcher_dm"
    _, session_id = table_for(dm_user, {user_id: "player"})

    with client.websocket_connect(
        f"/ws/mobile-companion/{session_id}?peer_id=peer_marcus",
        subprotocols=ws_subprotocols(user_id),
    ) as ws:
        _ = ws.receive_json()  # Consume connected frame

        # Dispatch secret whisper via public HTTP frontdoor
        whisper_res = client.post(
            f"/api/v1/mobile/companion/{session_id}/whisper",
            headers={"Authorization": f"Bearer {trusted_ws_issuer.mint(dm_user)}"},
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
            headers={"Authorization": f"Bearer {trusted_ws_issuer.mint(dm_user)}"},
            json={"recipient_id": user_id, "character_name": "Marcus", "round_num": 2},
        )
        assert alert_res.status_code == 200
        turn_frame = ws.receive_json()
        assert turn_frame["type"] == "haptic_ping"
        assert turn_frame["alert_type"] == "turn_alert"
        assert turn_frame["notification"]["turn_alert"] is True
        assert turn_frame["vibration_pattern"] == [300, 150, 300]
