"""Blackbox TDD tests for WebRTC Voice Room Zanzibar Authorization & Credential Extraction.

Governing ADRs: ADR-0001, ADR-0003, ADR-0007, ADR-0009.
Interacts strictly through public frontdoors:
  - WebSocket `/ws/voice/{session_id}`
Verifies:
  - Zanzibar permission rejection (4003, PERMISSION_DENIED)
  - Authorized connection handshakes (connected, webrtc_joined)
  - Credential extraction variants (query params, headers, guest fallback)
  - CloudEvent publishing on connect/disconnect
  - Backward compatibility of gateway_api.webrtc_signaling facade
"""

import asyncio
import json

import gateway_api.signaling as sig_pkg
import gateway_api.webrtc_signaling as sig_facade
import pytest
import voice_agent.main as va_main
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.main import app, set_event_bus
from gateway_api.signaling import signaling_manager
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from voice_agent.room import VoiceRoomCoordinator, set_voice_room_coordinator


@pytest.fixture(autouse=True)
def reset_voice_signaling_environment():
    """Reset SpiceDB client, Redis event bus, and voice room coordinator before each test."""
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)

    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    va_main.set_event_bus(bus)

    coord = VoiceRoomCoordinator(event_bus=bus, spicedb_client=mock_spicedb)
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
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)
    set_voice_room_coordinator(None)


def test_voice_websocket_connect_unauthorized_subject_rejected():
    """Subject lacking Zanzibar permissions is rejected with PERMISSION_DENIED and closed with 4003."""
    client = TestClient(app)
    session_id = "sess-unauth-test"

    with client.websocket_connect(
        f"/ws/voice/{session_id}?user_id=stranger_bob&peer_id=peer_bob"
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
        f"/ws/voice/{session_id}?user_id={user_id}&peer_id=peer_alice&role=player"
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


def test_voice_websocket_credential_extraction_variants():
    """Verify header and bearer token auth extraction and fallback to guest."""
    spicedb = get_spicedb_client()
    session_id = "sess-cred-variants"

    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", "bearer_user"))
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", "guest_user"))

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/voice/{session_id}",
        headers={"Authorization": "Bearer bearer_user"},
    ) as ws:
        msg = ws.receive_json()
        assert msg["user_id"] == "bearer_user"
        assert msg["peer_id"] == "peer_bearer_user"

    with client.websocket_connect(f"/ws/voice/{session_id}") as ws:
        msg = ws.receive_json()
        assert msg["user_id"] == "guest_user"
        assert msg["peer_id"] == "peer_guest_user"


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
        f"/ws/voice/{session_id}?user_id={user_id}&peer_id=peer_valeros&role=player"
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


def test_signaling_facade_and_submodule_backward_compatibility():
    """Verify facade re-exports identical objects as the modular signaling submodules."""
    assert sig_facade.WebRTCSignalingManager is sig_pkg.WebRTCSignalingManager
    assert sig_facade.signaling_manager is sig_pkg.signaling_manager
    assert sig_facade.extract_signaling_auth is sig_pkg.extract_signaling_auth
    assert sig_facade.validate_voice_connection is sig_pkg.validate_voice_connection
    assert (
        sig_facade.voice_signaling_websocket_endpoint is sig_pkg.voice_signaling_websocket_endpoint
    )
