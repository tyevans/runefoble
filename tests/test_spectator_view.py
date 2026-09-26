"""Tests for TASK-0014: Real-Time Spectator Stream & Chronicle Clean Overlay."""

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from gateway_api.spectator import (
    clear_raw_session_state,
    sanitize_spectator_state,
    set_raw_session_state,
)
from runefoble_events import SpectatorSessionConnected
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean spectator state and bus before and after each test."""
    clear_raw_session_state()
    set_event_bus(None)
    yield
    clear_raw_session_state()
    set_event_bus(None)


# ---------------------------------------------------------------------------
# 1. Event Registration & CloudEvents Compliance Tests
# ---------------------------------------------------------------------------


def test_spectator_session_connected_event_registration():
    """Verify SpectatorSessionConnected is properly registered in eventsource EventRegistry."""
    event_cls = get_event_class_or_none("runefoble.events.spectator.connected")
    assert event_cls is not None
    assert event_cls is SpectatorSessionConnected

    event = SpectatorSessionConnected(
        session_id="session-alpha",
        viewer_id="viewer-101",
        viewer_name="TwitchSpectator",
        connected_at="2026-09-26T04:00:00Z",
    )
    assert event.aggregate_type == "Spectator"
    assert event.session_id == "session-alpha"
    assert event.viewer_id == "viewer-101"
    assert event.viewer_name == "TwitchSpectator"


def test_spectator_session_connected_cloudevents_compliance():
    """Verify SpectatorSessionConnected satisfies standard CloudEvents 1.0 schema."""
    event = SpectatorSessionConnected(
        session_id="session-ce-1",
        viewer_id="obs_source_main",
        viewer_name="OBS Stream Source",
        connected_at="2026-09-26T04:15:00Z",
    )
    ce = event.to_cloudevent_dict()

    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.spectator.connected"
    assert ce["source"] == f"/runefoble/spectator/{event.aggregate_id}"
    assert ce["datacontenttype"] == "application/json"
    assert ce["data"]["session_id"] == "session-ce-1"
    assert ce["data"]["viewer_id"] == "obs_source_main"
    assert ce["data"]["viewer_name"] == "OBS Stream Source"
    assert ce["data"]["connected_at"] == "2026-09-26T04:15:00Z"


# ---------------------------------------------------------------------------
# 2. State Sanitization Logic Tests
# ---------------------------------------------------------------------------


def test_sanitize_spectator_state_strips_hidden_tokens_and_secret_notes():
    """Verify that hidden tokens, monster stat blocks, and private notes are completely stripped."""
    raw_state = {
        "session_id": "sess-san-1",
        "status": "active",
        "round": 4,
        "cols": 10,
        "rows": 10,
        "tokens": [
            {
                "id": "t-valeros",
                "name": "Valeros",
                "x": 2,
                "y": 3,
                "color": "#2563eb",
                "conditions": ["Blessed"],
                "hp": 45,
                "max_hp": 45,
                "ac": 18,
                "dm_notes": "Carries secret map.",
            },
            {
                "id": "t-kyra",
                "name": "Kyra",
                "x": 3,
                "y": 3,
                "color": "#db2777",
                "conditions": ["Drunk (Missed Session)"],
                "is_ai_controlled": True,
                "hp": 28,
                "max_hp": 32,
            },
            {
                "id": "t-hidden-scout",
                "name": "Goblin Scout",
                "x": 7,
                "y": 7,
                "hidden": True,
                "hp": 10,
                "stat_block": {"cr": "1/4", "stealth": "+6"},
            },
            {
                "id": "t-secret-mimic",
                "name": "Treasure Chest",
                "x": 5,
                "y": 5,
                "is_secret": True,
                "hp": 58,
                "dm_notes": "Mimic waiting to strike.",
            },
            {
                "id": "t-phantom",
                "name": "Shadow Phantom",
                "x": 1,
                "y": 1,
                "is_hidden": True,
                "hp": 30,
            },
        ],
        "dm_notes": "Secret GM encounter notes: Trap at (5,5), DC 15 Dex save or 3d6 poison.",
        "monster_stat_blocks": {
            "goblin_scout": {"cr": "1/4", "hp": 10, "ac": 13},
            "mimic": {"cr": "2", "hp": 58, "ac": 12},
        },
        "atmosphere": {
            "location_name": "Forgotten Sepulcher",
            "lighting": "Pale eerie luminescence",
            "mood": "Ominous",
            "description": "Granite walls sweat ancient moisture.",
            "ambient_audio_prompt": "dripping water, distant scraping",
            "private_dm_lore": "This was the resting place of Emperor Taraph.",
        },
        "chronicle": [
            {
                "id": "c1",
                "speaker": "Valeros",
                "text": "I ready my sword and shield.",
                "timestamp": "2026-09-26T04:20:00Z",
                "action_type": "speech",
            },
            {
                "id": "c2",
                "speaker": "The Watcher",
                "text": "The crypt air is heavy with suspense.",
                "timestamp": "2026-09-26T04:20:05Z",
                "action_type": "dm_ruling",
            },
            {
                "id": "c_secret",
                "speaker": "The Watcher (Private Note)",
                "text": "Secret DC 14 stealth check passed by goblin.",
                "timestamp": "2026-09-26T04:20:06Z",
                "is_private": True,
            },
        ],
    }

    sanitized = sanitize_spectator_state(raw_state)

    # 1. Hidden tokens must be filtered out
    token_ids = [t["id"] for t in sanitized["tokens"]]
    assert "t-valeros" in token_ids
    assert "t-kyra" in token_ids
    assert "t-hidden-scout" not in token_ids
    assert "t-secret-mimic" not in token_ids
    assert "t-phantom" not in token_ids
    assert len(sanitized["tokens"]) == 2

    # 2. Token stat blocks and private DM notes must be redacted
    for t in sanitized["tokens"]:
        assert "hp" not in t
        assert "max_hp" not in t
        assert "ac" not in t
        assert "stat_block" not in t
        assert "dm_notes" not in t
        assert "name" in t
        assert "x" in t
        assert "y" in t
        assert "conditions" in t

    # 3. Root secret fields must NOT be present
    assert "dm_notes" not in sanitized
    assert "monster_stat_blocks" not in sanitized

    # 4. Private chronicle entries must be stripped
    chronicle_ids = [c["id"] for c in sanitized["chronicle"]]
    assert "c1" in chronicle_ids
    assert "c2" in chronicle_ids
    assert "c_secret" not in chronicle_ids

    # 5. Atmosphere retains public sensory info and strips private lore
    assert sanitized["atmosphere"]["location_name"] == "Forgotten Sepulcher"
    assert sanitized["atmosphere"]["mood"] == "Ominous"
    assert "private_dm_lore" not in sanitized["atmosphere"]


# ---------------------------------------------------------------------------
# 3. Gateway REST Endpoint Tests (FastAPI TestClient)
# ---------------------------------------------------------------------------


def test_get_spectator_state_default_endpoint():
    """Verify GET /api/v1/spectate/{session_id} returns 200 with sanitized state and guest viewer."""
    client = TestClient(gateway_app)
    res = client.get("/api/v1/spectate/sess-default-1")

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == "sess-default-1"
    assert data["status"] == "active"
    assert data["round"] == 3
    assert data["cols"] == 8
    assert data["rows"] == 8

    # Tokens must be sanitized: only visible tokens
    names = [t["name"] for t in data["tokens"]]
    assert "Valeros" in names
    assert "Kyra" in names
    assert "Goblin Stalker" not in names
    assert "Mimic Chest" not in names

    # Monster stats and secrets stripped
    for tok in data["tokens"]:
        assert "hp" not in tok
        assert "stat_block" not in tok
        assert "dm_notes" not in tok

    # Atmosphere and chronicle present
    assert data["atmosphere"]["location_name"] == "Tomb of the Star-Eater - Crypt Antechamber"
    assert len(data["chronicle"]) == 2  # c_secret stripped

    # Default guest viewer info
    assert data["viewer"]["viewer_id"] == "spectator_guest"
    assert data["viewer"]["viewer_name"] == "Guest Spectator"


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

    # 1. Via X-User-Id
    res_x = client.get("/api/v1/spectate/sess-header-1", headers={"X-User-Id": "spectator_sam"})
    assert res_x.status_code == 200
    assert res_x.json()["viewer"]["viewer_id"] == "spectator_sam"

    # 2. Via Bearer token
    res_bearer = client.get(
        "/api/v1/spectate/sess-header-2", headers={"Authorization": "Bearer twitch_streamer_7"}
    )
    assert res_bearer.status_code == 200
    assert res_bearer.json()["viewer"]["viewer_id"] == "viewer_twitch_streamer_7"


@pytest.mark.asyncio
async def test_spectator_connected_event_dispatched_to_redis_bus():
    """Verify that accessing the spectator endpoint dispatches SpectatorSessionConnected event to Redis."""
    mock_redis = MockAsyncRedis()
    mock_bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(mock_bus)

    client = TestClient(gateway_app)
    res = client.get("/api/v1/spectate/sess-event-stream?token=obs_overlay")
    assert res.status_code == 200

    # Verify event published to Redis stream 'runefoble.events.spectator'
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
