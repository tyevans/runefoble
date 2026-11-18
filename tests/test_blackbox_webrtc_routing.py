"""Blackbox TDD tests for WebRTC Voice Room Routing, Telemetry, and Moderation.

Governing ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0007, ADR-0009.
Interacts strictly through public frontdoors:
  - WebSocket `/ws/voice/{session_id}`
  - HTTP `GET /api/v1/voice/rooms/{session_id}`
  - HTTP `POST /api/v1/voice/rooms/{session_id}/kick`
"""

import asyncio

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.main import app
from gateway_api.signaling import signaling_manager
from runefoble_auth.factory import get_spicedb_client
from voice_agent.room import VoiceRoomCoordinator, set_voice_room_coordinator

from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers
from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer", "trusted_voice_issuer")


@pytest.fixture(autouse=True)
def reset_voice_signaling_environment(default_redis_event_bus, mock_bus):
    """Reset SpiceDB client, Redis event bus, and coordinator before each test."""
    mock_spicedb = get_spicedb_client()
    bus = default_redis_event_bus
    coord = VoiceRoomCoordinator(event_bus=bus)
    set_voice_room_coordinator(coord)
    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()
    signaling_manager._coordinator = coord
    coord.register_kick_callback(signaling_manager.handle_peer_kicked)
    yield {"spicedb": mock_spicedb, "redis": mock_bus, "bus": bus, "coordinator": coord}
    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()
    signaling_manager._coordinator = None
    set_voice_room_coordinator(None)


def test_multi_peer_signaling_offer_answer_and_ice_candidate_relay(gateway, table_for):
    """Verify end-to-end signaling handshake between multiple simulated peer clients."""
    user_a, user_b = "user_alice", "user_bob"
    _, session_id = table_for("dm_dora", {user_a: "player", user_b: "player"})

    client = gateway
    with client.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer_a", subprotocols=ws_subprotocols(user_a)
    ) as ws_a:
        ws_a.receive_json()
        ws_a.receive_json()
        with client.websocket_connect(
            f"/ws/voice/{session_id}?peer_id=peer_b", subprotocols=ws_subprotocols(user_b)
        ) as ws_b:
            ws_b.receive_json()
            ws_b.receive_json()
            announcement = ws_a.receive_json()
            assert (
                announcement["type"] == "webrtc_peer_joined" and announcement["peer_id"] == "peer_b"
            )

            # 1. Offer
            offer_sdp = {"type": "offer", "sdp": "v=0"}
            ws_a.send_json(
                {
                    "type": "webrtc_offer",
                    "from_peer": "peer_a",
                    "to_peer": "peer_b",
                    "sdp": offer_sdp,
                }
            )
            rx_offer = ws_b.receive_json()
            assert rx_offer["type"] == "webrtc_offer" and rx_offer["sdp"] == offer_sdp

            # 2. Answer
            answer_sdp = {"type": "answer", "sdp": "v=0"}
            ws_b.send_json(
                {
                    "type": "webrtc_answer",
                    "from_peer": "peer_b",
                    "to_peer": "peer_a",
                    "sdp": answer_sdp,
                }
            )
            rx_answer = ws_a.receive_json()
            assert rx_answer["type"] == "webrtc_answer" and rx_answer["sdp"] == answer_sdp

            # 3. ICE candidate
            cand = {"candidate": "candidate:1 1 UDP 1234 127.0.0.1 5000 typ host"}
            ws_a.send_json(
                {
                    "type": "webrtc_ice_candidate",
                    "from_peer": "peer_a",
                    "to_peer": "peer_b",
                    "candidate": cand,
                }
            )
            rx_ice = ws_b.receive_json()
            assert rx_ice["type"] == "webrtc_ice_candidate" and rx_ice["candidate"] == cand


def test_voice_mute_toggle_and_telemetry_reporting(gateway, table_for):
    """Verify mute toggles and telemetry updates broadcast to room and reflect in room state."""
    user_id = "user_cleric"
    _, session_id = table_for("dm_dora", {user_id: "player"})

    client = gateway
    with client.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer_cleric", subprotocols=ws_subprotocols(user_id)
    ) as ws:
        ws.receive_json()
        ws.receive_json()

        # Send mute toggle
        ws.send_json({"type": "webrtc_mute", "peer_id": "peer_cleric", "is_muted": True})
        mute_msg = ws.receive_json()
        assert mute_msg["type"] == "webrtc_peer_muted" and mute_msg["is_muted"] is True

        # Send telemetry
        ws.send_json(
            {
                "type": "webrtc_telemetry",
                "peer_id": "peer_cleric",
                "audio_level": 0.82,
                "latency_ms": 14.5,
                "is_speaking": True,
            }
        )

        res = client.get(f"/api/v1/voice/rooms/{session_id}", headers=voice_auth_headers(user_id))
        assert res.status_code == 200
        peer = res.json()["participants"][0]
        assert peer["peer_id"] == "peer_cleric" and peer["is_muted"] is True
        assert (
            peer["audio_level"] == 0.82
            and peer["latency_ms"] == 14.5
            and peer["is_speaking"] is True
        )


def test_dm_moderation_kick_unauthorized_fails_with_403():
    """Regular player attempting to kick another peer receives 403 Forbidden."""
    spicedb = get_spicedb_client()
    session_id, player_id = "sess-kick-forbidden", "player_rebel"
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", player_id))

    client = TestClient(app)
    res = client.post(
        f"/api/v1/voice/rooms/{session_id}/kick",
        headers=voice_auth_headers(player_id),
        json={"peer_id": "peer_target", "reason": "disruptive"},
    )
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "permission_denied"


def test_dm_moderation_kick_authorized_succeeds_and_disconnects_peer():
    """Authorized DM kicks peer: target receives kick frame and connection is closed with 4001."""
    spicedb = get_spicedb_client()
    session_id, dm_user, bad_user = "sess-dm-kick-success", "the_watcher_dm", "troll_user"
    for r, u in (("dungeon_master", dm_user), ("player", bad_user)):
        asyncio.run(spicedb.write_relationship("campaign", session_id, r, "user", u))
    asyncio.run(grant_voice_session(session_id, dm=dm_user, players=[bad_user]))

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer_troll", subprotocols=ws_subprotocols(bad_user)
    ) as ws:
        ws.receive_json()
        ws.receive_json()
        room_url = f"/api/v1/voice/rooms/{session_id}"
        assert (
            client.get(room_url, headers=voice_auth_headers(dm_user)).json()["participant_count"]
            == 1
        )

        kick_res = client.post(
            f"/api/v1/voice/rooms/{session_id}/kick",
            headers=voice_auth_headers(dm_user),
            json={"peer_id": "peer_troll", "reason": "mic_spam"},
        )
        assert kick_res.status_code == 200 and kick_res.json()["status"] == "kicked"

        kicked_frame = ws.receive_json()
        assert kicked_frame["type"] == "webrtc_kicked" and kicked_frame["reason"] == "mic_spam"

        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4001

    assert (
        client.get(room_url, headers=voice_auth_headers(dm_user)).json()["participant_count"] == 0
    )
