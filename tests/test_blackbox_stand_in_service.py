"""Blackbox integration tests for Stand-In Action and Absentee Recap Service Endpoints (TASK-0070, TASK-0003).

Verifies:
1. POST /api/v1/watcher/stand-in/act publishes StandInActionDecided and AbsencePenaltyApplied events.
2. POST /api/v1/sessions/{id}/turns/auto-pilot advances turn and records stand-in action.
3. POST /api/v1/watcher/stand-in/recap generates humorous chronicle recap for returning player.
"""

from uuid import uuid4

import pytest
from game_session.main import app as session_app
from game_session.main import set_event_bus as session_set_event_bus
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import AbsencePenaltyApplied, StandInActionDecided
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


# ---------------------------------------------------------------------------
# 1. The Watcher Stand-In Event Emission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watcher_stand_in_event_emission(mock_redis: MockAsyncRedis):
    """POST /api/v1/watcher/stand-in/act must publish StandInActionDecided and AbsencePenaltyApplied."""
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    session_id, campaign_id = str(uuid4()), str(uuid4())
    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/watcher/stand-in/act",
            json={
                "character_name": "Kyra",
                "character_class": "Cleric",
                "penalties": ["drunk", "foolishness"],
                "scene_context": "Orc raiders attacking bridge",
                "personality_traits": ["valiant"],
                "session_id": session_id,
                "campaign_id": campaign_id,
            },
        )
        assert resp.status_code == 200
        action_data = resp.json()
        assert action_data["character_name"] == "Kyra"
        assert action_data["dice_roll_required"] == "1d20-2"

    # Verify runefoble.events.watcher stream received events
    assert "runefoble.events.watcher" in mock_redis.streams
    watcher_entries = mock_redis.streams["runefoble.events.watcher"]
    assert len(watcher_entries) == 3  # 1 StandInActionDecided + 2 AbsencePenaltyApplied

    # First event: StandInActionDecided
    evt1 = deserialize_event(watcher_entries[0][1])
    assert isinstance(evt1, StandInActionDecided)
    assert evt1.character_name == "Kyra"
    assert "drunk" in evt1.penalties_applied
    assert "foolishness" in evt1.penalties_applied

    # Second event: AbsencePenaltyApplied ("drunk")
    evt2 = deserialize_event(watcher_entries[1][1])
    assert isinstance(evt2, AbsencePenaltyApplied)
    assert evt2.penalty_type == "drunk"
    assert evt2.imposed_by == "the_watcher"

    # Third event: AbsencePenaltyApplied ("foolishness")
    evt3 = deserialize_event(watcher_entries[2][1])
    assert isinstance(evt3, AbsencePenaltyApplied)
    assert evt3.penalty_type == "foolishness"


# ---------------------------------------------------------------------------
# 2. Game Session Auto-Pilot Turn
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_game_session_auto_pilot_turn(mock_redis: MockAsyncRedis):
    """POST /api/v1/sessions/{session_id}/turns/auto-pilot must advance turn and record stand-in action."""
    event_bus = RedisStreamsEventBus(client=mock_redis)
    session_set_event_bus(event_bus)

    transport = ASGITransport(app=session_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        campaign_id, char_id = str(uuid4()), str(uuid4())

        # 1. Create session
        create_res = await client.post(
            "/api/v1/sessions/create",
            json={
                "campaign_id": campaign_id,
                "title": "Tomb of Horror - Session 4",
                "dm_id": "the_watcher",
            },
        )
        assert create_res.status_code == 200
        session_id = create_res.json()["session_id"]

        # 2. Join player
        join_res = await client.post(
            f"/api/v1/sessions/{session_id}/join",
            json={
                "player_id": "sarah-cleric",
                "character_id": char_id,
                "character_name": "Kyra",
                "character_class": "Cleric",
            },
        )
        assert join_res.status_code == 200

        # 3. Start session
        start_res = await client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "active"
        assert start_res.json()["current_turn"] == 1

        # 4. Attempt auto-pilot when player is present -> Must fail with 400
        auto_pilot_fail = await client.post(
            f"/api/v1/sessions/{session_id}/turns/auto-pilot",
            json={"penalties": ["drunk"]},
        )
        assert auto_pilot_fail.status_code == 400
        assert "not marked as absent" in auto_pilot_fail.json()["detail"]

        # 5. Mark player absent / leave session
        leave_res = await client.post(
            f"/api/v1/sessions/{session_id}/leave",
            json={"player_id": "sarah-cleric", "reason": "Sick with flu"},
        )
        assert leave_res.status_code == 200
        assert leave_res.json()["participants"]["sarah-cleric"]["is_stand_in_active"] is True

        # 6. Now execute auto-pilot turn
        auto_pilot_res = await client.post(
            f"/api/v1/sessions/{session_id}/turns/auto-pilot",
            json={
                "penalties": ["drunk"],
                "scene_context": "Goblins attacking campsite",
                "personality_traits": ["valiant"],
            },
        )
        assert auto_pilot_res.status_code == 200
        turn_data = auto_pilot_res.json()
        assert turn_data["current_turn"] == 2
        assert turn_data["action"]["character_name"] == "Kyra"
        assert turn_data["action"]["dice_roll_required"] == "1d20-2"
        assert "Hic!" in turn_data["action"]["dialogue"]

        # 7. Verify session state persisted stand-in actions
        get_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert get_res.status_code == 200
        persisted_session = get_res.json()
        assert len(persisted_session["stand_in_actions"]) == 1
        assert persisted_session["stand_in_actions"][0]["character_name"] == "Kyra"

    # Verify event publication to Redis
    assert "runefoble.events.watcher" in mock_redis.streams
    events = [
        deserialize_event(fields) for _, fields in mock_redis.streams["runefoble.events.watcher"]
    ]
    action_events = [e for e in events if isinstance(e, StandInActionDecided)]
    penalty_events = [e for e in events if isinstance(e, AbsencePenaltyApplied)]
    assert len(action_events) >= 1
    assert len(penalty_events) >= 1
    assert action_events[0].character_name == "Kyra"
    assert penalty_events[0].penalty_type == "drunk"


# ---------------------------------------------------------------------------
# 3. Absentee Session Recap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_absentee_session_recap_generation():
    """POST /api/v1/watcher/stand-in/recap must generate a humorous chronicle for the returning player."""
    transport = ASGITransport(app=watcher_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        recap_res = await client.post(
            "/api/v1/watcher/stand-in/recap",
            json={
                "character_name": "Kyra",
                "penalties": ["drunk", "foolishness"],
                "actions": [
                    {
                        "action_description": "Kyra swayed on her heels, hiccuping loudly, before swinging at a shadow.",
                        "dialogue": '"Hic! The ale only sharpens my blade!"',
                        "penalties_applied": ["drunk"],
                    },
                    {
                        "action_description": "Kyra recklessly charged headfirst towards an ancient red dragon.",
                        "dialogue": '"Danger? Ha! I eat danger for breakfast!"',
                        "penalties_applied": ["foolishness"],
                    },
                ],
            },
        )
        assert recap_res.status_code == 200
        recap_data = recap_res.json()

        assert recap_data["character_name"] == "Kyra"
        assert "Welcome back, Kyra!" in recap_data["recap"]
        assert "drunk" in recap_data["recap"]
        assert "foolishness" in recap_data["recap"]
        assert len(recap_data["highlights"]) == 2
        assert "drunk" in recap_data["penalties_active"]
        assert "foolishness" in recap_data["penalties_active"]
