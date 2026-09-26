"""Spectator Stream Overlay and Real-Time Broadcast Blackbox Suite.

Validates:
1. Public HTTP endpoints: GET /api/v1/spectate/{id} and /api/v1/spectator/sessions/{id}.
2. Viewer identification via token query parameters and authentication headers.
3. Event bus dispatch of SpectatorSessionConnected.
4. Dynamic session state injection and spectator state sanitization.
5. Live WebSocket /ws/spectator/{id} connect handshake and real-time broadcast updates.
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.cinematic_director import clear_cinematic_directors
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from gateway_api.spectator import (
    clear_raw_session_state,
    set_raw_session_state,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean spectator state and bus before and after each test."""
    clear_raw_session_state()
    clear_cinematic_directors()
    set_event_bus(None)
    yield
    clear_raw_session_state()
    clear_cinematic_directors()
    set_event_bus(None)


def test_get_spectator_state_endpoints():
    """Verify GET /api/v1/spectate/{id} and /api/v1/spectator/sessions/{id} return sanitized state."""
    client = TestClient(gateway_app)

    for path in ("/api/v1/spectate/sess-default-1", "/api/v1/spectator/sessions/sess-default-1"):
        res = client.get(path)
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == "sess-default-1"
        assert data["status"] == "active"
        assert data["round"] == 3

        names = [t["name"] for t in data["tokens"]]
        assert "Valeros" in names
        assert "Kyra" in names
        assert "Goblin Stalker" not in names
        assert "Mimic Chest" not in names

        for tok in data["tokens"]:
            assert "hp" not in tok
            assert "stat_block" not in tok
            assert "dm_notes" not in tok

        assert data["atmosphere"]["location_name"] == "Tomb of the Star-Eater - Crypt Antechamber"
        assert len(data["chronicle"]) == 2
        assert data["viewer"]["viewer_id"] == "spectator_guest"


def test_get_spectator_state_with_token_query():
    """Verify spectator authentication and viewer tagging via ?token= query parameter."""
    client = TestClient(gateway_app)
    res = client.get("/api/v1/spectate/sess-obs-1?token=devon_stream")
    assert res.status_code == 200
    data = res.json()
    assert data["viewer"]["viewer_id"] == "spectator_devon_stream"
    assert data["viewer"]["viewer_name"] == "Spectator (devon_stream)"


def test_get_spectator_state_with_auth_headers():
    """Verify viewer identity resolution from X-User-Id and Authorization bearer headers."""
    client = TestClient(gateway_app)

    res_x = client.get("/api/v1/spectate/sess-header-1", headers={"X-User-Id": "spectator_sam"})
    assert res_x.status_code == 200
    assert res_x.json()["viewer"]["viewer_id"] == "spectator_sam"

    res_bearer = client.get(
        "/api/v1/spectate/sess-header-2", headers={"Authorization": "Bearer twitch_streamer_7"}
    )
    assert res_bearer.status_code == 200
    assert res_bearer.json()["viewer"]["viewer_id"] == "viewer_twitch_streamer_7"


@pytest.mark.asyncio
async def test_spectator_connected_event_dispatched_to_redis_bus():
    """Verify that accessing spectator endpoint dispatches SpectatorSessionConnected to Redis."""
    mock_redis = MockAsyncRedis()
    mock_bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(mock_bus)

    client = TestClient(gateway_app)
    res = client.get("/api/v1/spectate/sess-event-stream?token=obs_overlay")
    assert res.status_code == 200

    stream_events = mock_redis.streams.get("runefoble.events.spectator", [])
    assert len(stream_events) == 1

    _event_id, payload = stream_events[0]
    assert payload["event_type"] == "runefoble.events.spectator.connected"
    assert "sess-event-stream" in payload["payload"]
    assert "spectator_obs_overlay" in payload["payload"]


def test_custom_session_state_overrides_and_sanitization():
    """Verify custom session state can be dynamically provided and is properly sanitized."""
    custom_raw = {
        "session_id": "custom-dungeon-5",
        "status": "in_combat",
        "round": 6,
        "cols": 12,
        "rows": 12,
        "tokens": [
            {"id": "c-hero", "name": "Hero", "x": 1, "y": 1, "hp": 100, "ac": 20},
            {"id": "c-stealth", "name": "Stalker", "x": 4, "y": 4, "secret": True, "hp": 40},
        ],
        "dm_notes": "Trap triggered if hero moves east.",
        "chronicle": [
            {"id": "ch-1", "speaker": "Hero", "text": "For the realm!", "timestamp": "12:00:00"},
        ],
    }
    set_raw_session_state("custom-dungeon-5", custom_raw)

    client = TestClient(gateway_app)
    res = client.get("/api/v1/spectate/custom-dungeon-5")
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == "custom-dungeon-5"
    assert data["round"] == 6
    assert data["cols"] == 12
    assert len(data["tokens"]) == 1
    assert data["tokens"][0]["id"] == "c-hero"
    assert "hp" not in data["tokens"][0]
    assert "dm_notes" not in data


def test_spectator_websocket_connection_and_initial_stream_state():
    """Verify live WebSocket /ws/spectator/{id} connects and delivers sanitized party state."""
    client = TestClient(gateway_app)
    with client.websocket_connect("/ws/spectator/sess-ws-spec-1") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "overlay_connected"
        assert msg["session_id"] == "sess-ws-spec-1"
        assert msg["transparent"] is True

        party_names = [p["name"] for p in msg["party"]]
        assert "Valeros" in party_names
        assert "Kyra" in party_names
        assert "Goblin Stalker" not in party_names
        assert "Mimic Chest" not in party_names

        for member in msg["party"]:
            assert "stat_block" not in member
            assert "dm_notes" not in member
            assert "ac" not in member


def test_spectator_websocket_realtime_broadcast_updates():
    """Verify live WebSocket receives camera updates upon turn start and token move events."""
    client = TestClient(gateway_app)
    with client.websocket_connect("/ws/spectator/sess-ws-events-spec") as ws:
        _init = ws.receive_json()

        # 1. Turn Started -> broadcast camera centering
        ws.send_json({"action": "turn_started", "character_id": "c-valeros", "token_id": "t1"})
        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "camera_target_updated"
        assert turn_msg["action"] == "turn_started"
        assert turn_msg["camera"]["duration_ms"] == 300

        # 2. Token Moved -> broadcast camera centering
        ws.send_json(
            {
                "action": "token_moved",
                "token_id": "t1",
                "from_x": 2,
                "from_y": 3,
                "to_x": 4,
                "to_y": 4,
            }
        )
        move_msg = ws.receive_json()
        assert move_msg["type"] == "camera_target_updated"
        assert move_msg["action"] == "token_moved"
        assert move_msg["camera"]["target_x"] == 4.0
