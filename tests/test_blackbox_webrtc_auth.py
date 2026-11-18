"""Blackbox TDD tests for WebRTC Voice Room Zanzibar Authorization & Credential Extraction.

Governing ADRs: ADR-0001, ADR-0003, ADR-0007, ADR-0009.
Interacts strictly through public frontdoors:
  - WebSocket `/ws/voice/{session_id}`
Verifies:
  - `session.observe` rejection (close code 4403)
  - Authorized connection handshakes (connected, webrtc_joined)
  - Credential extraction variants (query params, headers, guest fallback)
  - CloudEvent publishing on connect/disconnect
"""

import json
import time

import pytest
from fastapi import WebSocketDisconnect
from runefoble_auth.factory import get_spicedb_client
from voice_agent.coordinator import (
    VoiceRoomCoordinator,
    get_voice_room_coordinator,
    set_voice_room_coordinator,
)
from voice_agent.signaling import signaling_manager

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture(autouse=True)
def reset_voice_signaling_environment(
    default_redis_event_bus, mock_bus, seam_restorer: SeamRestorer
):
    """Reset SpiceDB client, Redis event bus, and voice room coordinator before each test."""
    mock_spicedb = get_spicedb_client()

    bus = default_redis_event_bus

    coord = VoiceRoomCoordinator(event_bus=bus)
    seam_restorer.replace(get_voice_room_coordinator, set_voice_room_coordinator, coord)
    previous_manager_coordinator = signaling_manager._coordinator

    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()
    signaling_manager._coordinator = coord
    coord.register_kick_callback(signaling_manager.handle_peer_kicked)

    yield {
        "spicedb": mock_spicedb,
        "redis": mock_bus,
        "bus": bus,
        "coordinator": coord,
    }

    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()
    signaling_manager._coordinator = previous_manager_coordinator


def test_voice_websocket_connect_unauthorized_subject_rejected(gateway, table_for):
    """A subject without `session.observe` is refused with close code 4403."""
    _, session_id = table_for("dm_dora")

    with (
        pytest.raises(WebSocketDisconnect) as exc,
        gateway.websocket_connect(
            f"/ws/voice/{session_id}?peer_id=peer_bob", subprotocols=ws_subprotocols("stranger_bob")
        ) as ws,
    ):
        ws.receive_json()
    assert exc.value.code == 4403


def test_voice_websocket_connect_authorized_subject_succeeds(gateway, table_for):
    """Subject with Zanzibar session participation succeeds and receives connected and joined frames."""
    user_id = "alice_player"
    _, session_id = table_for("dm_dora", {user_id: "player"})

    with gateway.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer_alice&role=player",
        subprotocols=ws_subprotocols(user_id),
    ) as ws:
        connected_frame = ws.receive_json()
        assert connected_frame["type"] == "connected"
        assert connected_frame["session_id"] == session_id
        assert connected_frame["peer_id"] == "peer_alice"

        joined_frame = ws.receive_json()
        assert joined_frame["type"] == "webrtc_joined"
        assert joined_frame["session_id"] == session_id
        assert joined_frame["peer_id"] == "peer_alice"
        assert joined_frame["user_id"] == user_id
        assert len(joined_frame["peers"]) == 1
        assert joined_frame["peers"][0]["peer_id"] == "peer_alice"


def test_voice_websocket_identity_comes_only_from_verified_token(gateway, table_for):
    """Verify the voice socket admits only a verified bearer subprotocol. No guest fallback."""
    _, session_id = table_for("dm_dora", {"bearer_user": "player"})
    client = gateway
    with client.websocket_connect(
        f"/ws/voice/{session_id}", subprotocols=ws_subprotocols("bearer_user")
    ) as ws:
        msg = ws.receive_json()
        assert msg["user_id"] == "bearer_user"
        assert msg["peer_id"] == "peer_bearer_user"

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/voice/{session_id}"):
        pass

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/ws/voice/{session_id}", headers={"Authorization": "Bearer bearer_user"}
        ),
    ):
        pass


def test_voice_peer_lifecycle_events_published_to_redis(
    reset_voice_signaling_environment, gateway, table_for
):
    """Verifies VoicePeerJoined and VoicePeerLeft events are published to runefoble.events.session."""
    env = reset_voice_signaling_environment
    redis: MockAsyncRedis = env["redis"]
    user_id = "valeros_user"
    _, session_id = table_for("dm_dora", {user_id: "player"})

    with gateway.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer_valeros&role=player",
        subprotocols=ws_subprotocols(user_id),
    ) as ws:
        _ = ws.receive_json()
        _ = ws.receive_json()

        session_events = redis.streams.get("runefoble.events.session", [])
        assert len(session_events) >= 1
        raw_payload = json.dumps(session_events[-1][1])
        assert "peer_valeros" in raw_payload
        assert "valeros_user" in raw_payload

        ws.send_json({"type": "webrtc_leave", "peer_id": "peer_valeros", "reason": "left_session"})

    # The owner handles the leave frame on its own loop. Wait for the event it publishes.
    deadline = time.monotonic() + 5.0
    while True:
        session_events = redis.streams.get("runefoble.events.session", [])
        if any("peer_valeros" in str(e[1]) and "left_session" in str(e[1]) for e in session_events):
            break
        assert time.monotonic() < deadline, "peer left event was not published"
        time.sleep(0.05)
