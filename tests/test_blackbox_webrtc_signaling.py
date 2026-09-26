"""Blackbox TDD tests for TASK-0033: Live WebRTC Bidirectional Voice Room Signaling & WebAudio Pipeline.

Interacts strictly through public frontdoors:
  - WebSocket `/ws/voice/{session_id}`
  - HTTP `GET /api/v1/voice/rooms/{session_id}`
  - HTTP `POST /api/v1/voice/rooms/{session_id}/kick`
Verifies Zanzibar object authorization, multi-peer WebRTC signaling (join, offer,
answer, trickle ICE), mute toggling, telemetry, DM moderation, and emitted domain events.
"""

import asyncio
import json

import pytest
import voice_agent.main as va_main
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.main import app, set_event_bus
from gateway_api.webrtc_signaling import signaling_manager
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

    set_voice_room_coordinator(None)


def test_voice_websocket_connect_unauthorized_subject_rejected():
    """Subject lacking Zanzibar permissions is rejected with PERMISSION_DENIED and closed with 4003."""
    client = TestClient(app)
    session_id = "sess-unauth-test"

    # stranger_bob has no Zanzibar relation to campaign or session
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

    # Grant player permission in SpiceDB Zanzibar
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/voice/{session_id}?user_id={user_id}&peer_id=peer_alice&role=player"
    ) as ws:
        # Initial connected frame
        connected_frame = ws.receive_json()
        assert connected_frame["type"] == "connected"
        assert connected_frame["session_id"] == session_id
        assert connected_frame["peer_id"] == "peer_alice"

        # Joined confirmation frame with room peer list
        joined_frame = ws.receive_json()
        assert joined_frame["type"] == "webrtc_joined"
        assert joined_frame["session_id"] == session_id
        assert joined_frame["peer_id"] == "peer_alice"
        assert joined_frame["user_id"] == user_id
        assert len(joined_frame["peers"]) == 1
        assert joined_frame["peers"][0]["peer_id"] == "peer_alice"


def test_voice_peer_lifecycle_events_published_to_redis_streams(reset_voice_signaling_environment):
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
        _ = ws.receive_json()  # connected
        _ = ws.receive_json()  # webrtc_joined

        # Verify VoicePeerJoined was published to session stream
        session_events = redis.streams.get("runefoble.events.session", [])
        assert len(session_events) >= 1
        last_entry = session_events[-1]
        fields = last_entry[1]
        raw_payload = fields.get("data") or fields.get("payload") or json.dumps(fields)
        assert "peer_valeros" in str(raw_payload)
        assert "valeros_user" in str(raw_payload)

        # Graceful leave via WebSocket signal
        ws.send_json({"type": "webrtc_leave", "peer_id": "peer_valeros", "reason": "left_session"})

    # Verify VoicePeerLeft event published
    session_events = redis.streams.get("runefoble.events.session", [])
    left_events = [
        e for e in session_events if "peer_valeros" in str(e[1]) and "left_session" in str(e[1])
    ]
    assert len(left_events) >= 1


def test_multi_peer_signaling_offer_answer_and_ice_candidate_relay():
    """Verify end-to-end signaling handshake between multiple simulated peer clients."""
    spicedb = get_spicedb_client()
    session_id = "sess-signaling-mesh"
    user_a = "user_alice"
    user_b = "user_bob"

    # Grant Zanzibar permissions
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_a))
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_b))

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/voice/{session_id}?user_id={user_a}&peer_id=peer_a&role=player"
    ) as ws_a:
        _ = ws_a.receive_json()  # connected
        _ = ws_a.receive_json()  # webrtc_joined

        # Connect peer B
        with client.websocket_connect(
            f"/ws/voice/{session_id}?user_id={user_b}&peer_id=peer_b&role=player"
        ) as ws_b:
            _ = ws_b.receive_json()  # connected
            _ = ws_b.receive_json()  # webrtc_joined

            # Peer A should receive notification that peer B joined
            announcement = ws_a.receive_json()
            assert announcement["type"] == "webrtc_peer_joined"
            assert announcement["peer_id"] == "peer_b"

            # 1. Peer A sends SDP Offer to Peer B
            offer_sdp = {"type": "offer", "sdp": "v=0\r\no=alice 12345 IN IP4 0.0.0.0"}
            ws_a.send_json(
                {
                    "type": "webrtc_offer",
                    "from_peer": "peer_a",
                    "to_peer": "peer_b",
                    "sdp": offer_sdp,
                }
            )

            # Peer B receives the offer
            received_offer = ws_b.receive_json()
            assert received_offer["type"] == "webrtc_offer"
            assert received_offer["from_peer"] == "peer_a"
            assert received_offer["to_peer"] == "peer_b"
            assert received_offer["sdp"] == offer_sdp

            # 2. Peer B replies with SDP Answer to Peer A
            answer_sdp = {"type": "answer", "sdp": "v=0\r\no=bob 67890 IN IP4 0.0.0.0"}
            ws_b.send_json(
                {
                    "type": "webrtc_answer",
                    "from_peer": "peer_b",
                    "to_peer": "peer_a",
                    "sdp": answer_sdp,
                }
            )

            # Peer A receives the answer
            received_answer = ws_a.receive_json()
            assert received_answer["type"] == "webrtc_answer"
            assert received_answer["from_peer"] == "peer_b"
            assert received_answer["sdp"] == answer_sdp

            # 3. Peer A sends trickle ICE Candidate to Peer B
            candidate_payload = {
                "candidate": "candidate:1 1 UDP 2122252543 192.168.1.1 54321 typ host"
            }
            ws_a.send_json(
                {
                    "type": "webrtc_ice_candidate",
                    "from_peer": "peer_a",
                    "to_peer": "peer_b",
                    "candidate": candidate_payload,
                }
            )

            # Peer B receives trickle ICE candidate
            received_ice = ws_b.receive_json()
            assert received_ice["type"] == "webrtc_ice_candidate"
            assert received_ice["from_peer"] == "peer_a"
            assert received_ice["candidate"] == candidate_payload


def test_voice_mute_toggle_and_telemetry_reporting():
    """Verify mute toggles and telemetry updates broadcast to room and reflect in room state."""
    spicedb = get_spicedb_client()
    session_id = "sess-mute-telemetry"
    user_id = "user_cleric"

    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", user_id))

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/voice/{session_id}?user_id={user_id}&peer_id=peer_cleric&role=player"
    ) as ws:
        _ = ws.receive_json()
        _ = ws.receive_json()

        # 1. Send mute toggle
        ws.send_json({"type": "webrtc_mute", "peer_id": "peer_cleric", "is_muted": True})
        mute_broadcast = ws.receive_json()
        assert mute_broadcast["type"] == "webrtc_peer_muted"
        assert mute_broadcast["peer_id"] == "peer_cleric"
        assert mute_broadcast["is_muted"] is True

        # 2. Send telemetry
        ws.send_json(
            {
                "type": "webrtc_telemetry",
                "peer_id": "peer_cleric",
                "audio_level": 0.82,
                "latency_ms": 14.5,
                "is_speaking": True,
            }
        )

        # 3. Query frontdoor GET /api/v1/voice/rooms/{session_id}
        res = client.get(f"/api/v1/voice/rooms/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == session_id
        assert data["participant_count"] == 1
        peer = data["participants"][0]
        assert peer["peer_id"] == "peer_cleric"
        assert peer["is_muted"] is True
        assert peer["audio_level"] == 0.82
        assert peer["latency_ms"] == 14.5
        assert peer["is_speaking"] is True


def test_dm_moderation_kick_unauthorized_fails_with_403():
    """Regular player attempting to kick another peer receives 403 Forbidden."""
    spicedb = get_spicedb_client()
    session_id = "sess-kick-forbidden"
    player_id = "player_rebel"

    # Only has player permission, not DM/control
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", player_id))

    client = TestClient(app)
    res = client.post(
        f"/api/v1/voice/rooms/{session_id}/kick",
        headers={"X-User-Id": player_id},
        json={"peer_id": "peer_target", "reason": "disruptive"},
    )
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "permission_denied"


def test_dm_moderation_kick_authorized_succeeds_and_disconnects_peer():
    """Authorized DM kicks peer: peer receives kick frame, WebSocket closes with 4001, room removes peer."""
    spicedb = get_spicedb_client()
    session_id = "sess-dm-kick-success"
    dm_user = "the_watcher_dm"
    bad_user = "troll_user"

    # DM has dungeon_master relation; target is player
    asyncio.run(
        spicedb.write_relationship("campaign", session_id, "dungeon_master", "user", dm_user)
    )
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", bad_user))

    client = TestClient(app)
    # Target peer connects
    with client.websocket_connect(
        f"/ws/voice/{session_id}?user_id={bad_user}&peer_id=peer_troll&role=player"
    ) as ws_troll:
        _ = ws_troll.receive_json()
        _ = ws_troll.receive_json()

        # Check room has 1 participant
        res_before = client.get(f"/api/v1/voice/rooms/{session_id}")
        assert res_before.json()["participant_count"] == 1

        # DM executes kick via HTTP POST /api/v1/voice/rooms/{session_id}/kick
        kick_res = client.post(
            f"/api/v1/voice/rooms/{session_id}/kick",
            headers={"X-User-Id": dm_user},
            json={"peer_id": "peer_troll", "reason": "mic_spam"},
        )
        assert kick_res.status_code == 200
        kick_data = kick_res.json()
        assert kick_data["status"] == "kicked"
        assert kick_data["peer_id"] == "peer_troll"
        assert kick_data["reason"] == "mic_spam"
        assert kick_data["kicked_by"] == dm_user

        # Target peer should receive kick frame
        kicked_frame = ws_troll.receive_json()
        assert kicked_frame["type"] == "webrtc_kicked"
        assert kicked_frame["reason"] == "mic_spam"

        # And target peer connection is disconnected with 4001
        with pytest.raises(WebSocketDisconnect) as exc:
            ws_troll.receive_json()
        assert exc.value.code == 4001

    # Verify querying GET /api/v1/voice/rooms/{session_id} reflects 0 participants
    res_after = client.get(f"/api/v1/voice/rooms/{session_id}")
    assert res_after.json()["participant_count"] == 0
