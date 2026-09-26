"""Unit and integration tests for Missing Player AI Stand-In Engine (TASK-0003).

Verifies:
1. Automated stand-in turn generation when player is marked absent.
2. "drunk" and "foolishness" (plus "cowardice", "greed") penalties modifying mechanics, dialogue, and flavor text.
3. Personality trait integration ("valiant", "impulsive", "scholarly") into stand-in tactics and roleplay.
4. Redis Streams event publication (StandInActionDecided, AbsencePenaltyApplied).
5. Absentee session recap generation for returning human players.
"""

from uuid import uuid4

import pytest
from game_session.main import app as session_app
from game_session.main import set_event_bus as session_set_event_bus
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import AbsencePenaltyApplied, StandInActionDecided
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
    deserialize_event,
)
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus
from the_watcher.watcher_ai import TheWatcherEngine


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def watcher_engine() -> TheWatcherEngine:
    return TheWatcherEngine()


# ---------------------------------------------------------------------------
# 1. Unit Tests: Stand-In Penalties & Personality Trait Mechanics
# ---------------------------------------------------------------------------


def test_stand_in_drunk_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'drunk' penalty must inflict disadvantage / roll penalty (1d20-2) and slurred speech."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["drunk"],
        scene_context="Goblins surrounding the campsite",
    )
    assert action.character_name == "Kyra"
    assert action.dice_roll_required == "1d20-2"
    assert "Hic!" in action.dialogue
    assert "Drunk" in (action.penalty_influence or "")
    assert "-2 penalty" in (action.penalty_influence or "")
    assert "sway" in action.action_description.lower()
    assert action.action_type == "attack"


def test_stand_in_foolishness_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'foolishness' penalty must create reckless distraction and impose disadvantage on enemies attacking allies."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Valeros",
        character_class="Fighter",
        penalties=["foolishness"],
        scene_context="Dragon lair encounter",
    )
    assert action.character_name == "Valeros"
    assert "danger" in action.dialogue.lower()
    assert "Foolishness" in (action.penalty_influence or "")
    assert "distraction" in (action.penalty_influence or "").lower()
    assert "disadvantage on enemy attacks" in (action.penalty_influence or "").lower()
    assert "recklessly" in action.action_description.lower()
    assert action.action_type == "attack"


def test_stand_in_cowardice_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'cowardice' penalty must trigger full defensive posturing and retreat behavior."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Merisiel",
        character_class="Rogue",
        penalties=["cowardice"],
        scene_context="Troll ambush",
    )
    assert action.character_name == "Merisiel"
    assert action.action_type == "defend"
    assert "Cowardice" in (action.penalty_influence or "")
    assert "defensive posture" in (action.penalty_influence or "").lower()
    assert "retreat" in (action.penalty_influence or "").lower()


def test_stand_in_greed_penalty_mechanics(watcher_engine: TheWatcherEngine):
    """'greed' penalty must prioritize looting and chest searching over tactical positioning."""
    action = watcher_engine.generate_stand_in_action(
        character_name="Ezren",
        character_class="Wizard",
        penalties=["greed"],
        scene_context="Ancient crypt fight",
    )
    assert action.character_name == "Ezren"
    assert action.action_type == "loot"
    assert "Greed" in (action.penalty_influence or "")
    assert "looting" in (action.penalty_influence or "").lower()


def test_personality_traits_alter_dialogue_and_tactics(watcher_engine: TheWatcherEngine):
    """Personality traits ('scholarly', 'valiant', 'impulsive') must flavor dialogue and action choices."""
    # Scholarly + Drunk
    scholarly_drunk = watcher_engine.generate_stand_in_action(
        character_name="Ezren",
        character_class="Wizard",
        penalties=["drunk"],
        scene_context="Library skirmish",
        personality_traits=["scholarly"],
    )
    assert (
        "Arcane Volume IV" in scholarly_drunk.dialogue
        or "statistically" in scholarly_drunk.dialogue
    )
    assert "slurring arcane citations" in scholarly_drunk.action_description

    # Valiant + Foolishness
    valiant_fool = watcher_engine.generate_stand_in_action(
        character_name="Valeros",
        character_class="Fighter",
        penalties=["foolishness"],
        scene_context="Colosseum battle",
        personality_traits=["valiant"],
    )
    assert "glory" in valiant_fool.dialogue.lower()
    assert "distraction" in valiant_fool.action_description
    assert "disadvantage on enemy attacks" in (valiant_fool.penalty_influence or "").lower()

    # Impulsive (no penalty)
    impulsive_action = watcher_engine.generate_stand_in_action(
        character_name="Merisiel",
        character_class="Rogue",
        penalties=[],
        scene_context="In combat",
        personality_traits=["impulsive"],
    )
    assert "strike hard and fast" in impulsive_action.dialogue.lower()


# ---------------------------------------------------------------------------
# 2. Integration Tests: Redis Streams Event Dispatching (The Watcher)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watcher_stand_in_event_emission(mock_redis: MockAsyncRedis):
    """POST /api/v1/watcher/stand-in/act must publish StandInActionDecided and AbsencePenaltyApplied."""
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    session_id = str(uuid4())
    campaign_id = str(uuid4())

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
    # 1 StandInActionDecided + 2 AbsencePenaltyApplied
    assert len(watcher_entries) == 3

    # First event: StandInActionDecided
    _id1, fields1 = watcher_entries[0]
    evt1 = deserialize_event(fields1)
    assert isinstance(evt1, StandInActionDecided)
    assert evt1.character_name == "Kyra"
    assert "drunk" in evt1.penalties_applied
    assert "foolishness" in evt1.penalties_applied

    # Second event: AbsencePenaltyApplied ("drunk")
    _id2, fields2 = watcher_entries[1]
    evt2 = deserialize_event(fields2)
    assert isinstance(evt2, AbsencePenaltyApplied)
    assert evt2.penalty_type == "drunk"
    assert evt2.imposed_by == "the_watcher"

    # Third event: AbsencePenaltyApplied ("foolishness")
    _id3, fields3 = watcher_entries[2]
    evt3 = deserialize_event(fields3)
    assert isinstance(evt3, AbsencePenaltyApplied)
    assert evt3.penalty_type == "foolishness"


# ---------------------------------------------------------------------------
# 3. Integration Tests: Game Session Auto-Pilot Turn
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_game_session_auto_pilot_turn(mock_redis: MockAsyncRedis):
    """POST /api/v1/sessions/{session_id}/turns/auto-pilot must advance turn and record stand-in action."""
    event_bus = RedisStreamsEventBus(client=mock_redis)
    session_set_event_bus(event_bus)

    transport = ASGITransport(app=session_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session
        campaign_id = str(uuid4())
        char_id = str(uuid4())

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
# 4. Integration Tests: Absentee Session Recap
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
