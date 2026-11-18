"""Blackbox TDD tests for WebRTC Voice Room Zanzibar Authorization & Credential Extraction.

Governing ADRs: ADR-0001, ADR-0003, ADR-0007, ADR-0009.
Interacts strictly through public frontdoors:
  - WebSocket `/ws/voice/{session_id}`
Verifies:
  - Zanzibar permission rejection (4003, PERMISSION_DENIED)
  - Authorized connection handshakes (connected, webrtc_joined)
  - Credential extraction variants (query params, headers, guest fallback)
  - CloudEvent publishing on connect/disconnect
"""

import asyncio
import json

import pytest
import voice_agent.main as va_main
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.main import app, set_event_bus
from gateway_api.signaling import signaling_manager
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus
from voice_agent.room import VoiceRoomCoordinator, set_voice_room_coordinator

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture(autouse=True)
def reset_voice_signaling_environment():
    """Reset SpiceDB client, Redis event bus, and voice room coordinator before each test."""
    mock_spicedb = get_spicedb_client()

    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    va_main.set_event_bus(bus)

    coord = VoiceRoomCoordinator(event_bus=bus)
    set_voice_room_coordinator(coord)

    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()
    signaling_manager._coordinator = coord
    coord.register_kick_callback(signaling_manager.handle_peer_kicked)

    yield {
        "spicedb": mock_spicedb,
        "redis": mock_redis,
        "bus": bus,
        "coordinator": coord,
    }

    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()
    signaling_manager._coordinator = None
    va_main.set_event_bus(None)
    set_event_bus(None)
    set_voice_room_coordinator(None)


def test_voice_websocket_connect_unauthorized_subject_rejected():
    """Subject lacking Zanzibar permissions is rejected with PERMISSION_DENIED and closed with 4003."""
    client = TestClient(app)
    session_id = "sess-unauth-test"

    with client.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer_bob", subprotocols=ws_subprotocols("stranger_bob")
    ) as ws:
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"
        assert err_msg["action"] == "connect"
        assert "insufficient permissions" in err_msg["message"]

        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4003


def test_voice_websocket_connect_authorized_subject_succeeds():
    """Subject with Zanzibar session participation succeeds and receives connected and joined frames."""
    spicedb = get_spicedb_client()
    session_id = "sess-auth-success"
    user_id = "alice_player"

    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))

    client = TestClient(app)
    with client.websocket_connect(
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


def test_voice_websocket_identity_comes_only_from_verified_token():
    """Verify the voice socket admits only a verified bearer subprotocol. No guest fallback."""
    spicedb = get_spicedb_client()
    session_id = "sess-cred-variants"

    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", "bearer_user"))

    client = TestClient(app)
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


def test_voice_peer_lifecycle_events_published_to_redis(reset_voice_signaling_environment):
    """Verifies VoicePeerJoined and VoicePeerLeft events are published to runefoble.events.session."""
    env = reset_voice_signaling_environment
    spicedb: MockSpiceDBClient = env["spicedb"]
    redis: MockAsyncRedis = env["redis"]
    session_id = "sess-lifecycle-events"
    user_id = "valeros_user"

    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))

    client = TestClient(app)
    with client.websocket_connect(
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

    session_events = redis.streams.get("runefoble.events.session", [])
    assert any("peer_valeros" in str(e[1]) and "left_session" in str(e[1]) for e in session_events)
