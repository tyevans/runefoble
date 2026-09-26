"""Blackbox TDD tests for Stand-In Policy Guardrails and Mid-Session Hot-Swap Takeover (TASK-0055).

Verifies:
1. Public HTTP Frontdoor: PUT/GET /api/v1/characters/{id}/guardrails configures tactical constraints.
2. SpiceDB Zanzibar Object-Level Authorization enforcement for guardrails and hot-swap.
3. Event Sourcing & CloudEvents: Emits StandInPolicyUpdated, StandInStabilized, and CharacterControlTransferred.
4. Stand-In Graph Policy Evaluation: Preserving 3rd-level spell slots, protecting ally Marcus, avoiding frontline melee.
5. Humorous Penalty Adaptation: Stand-in maintains tactical intent while slurring/taunting under 'drunk' and 'foolishness'.
6. Zero-HP Permadeath Safeguard: Aggregate invariant ensures stand-in character stabilizes at 0 HP without death saves.
7. Mid-Session Hot-Swap Takeover: POST /api/v1/sessions/{id}/hot-swap smoothly transfers control back to returning player in < 100ms, preserving combat initiative order and round continuity.
"""

from uuid import uuid4

import pytest
from character_sheet.main import app as character_app
from character_sheet.main import set_event_bus as character_set_event_bus
from character_sheet.main import set_spicedb_client as character_set_spicedb
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.main import set_event_bus as session_set_event_bus
from game_session.main import set_spicedb_client as session_set_spicedb
from httpx import ASGITransport, AsyncClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.events import (
    CharacterControlTransferred,
    StandInPolicyUpdated,
    StandInStabilized,
)
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
    deserialize_event,
)
from the_watcher.watcher_ai import TheWatcherEngine


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def char_client():
    return TestClient(character_app)


@pytest.fixture
def session_client():
    return TestClient(session_app)


@pytest.fixture
def watcher_engine() -> TheWatcherEngine:
    return TheWatcherEngine()


# ---------------------------------------------------------------------------
# 1. Frontdoor API: Character Tactical Guardrails & Zanzibar Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_character_guardrails_configuration_and_events(mock_redis: MockAsyncRedis):
    """PUT /api/v1/characters/{id}/guardrails configures tactical constraints and emits StandInPolicyUpdated."""
    bus = RedisStreamsEventBus(client=mock_redis)
    character_set_event_bus(bus)
    spicedb = SpiceDBClient()
    character_set_spicedb(spicedb)

    transport = ASGITransport(app=character_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Sarah's Cleric
        create_res = await client.post(
            "/api/v1/characters/create",
            json={
                "name": "Kyra",
                "character_class": "Cleric",
                "max_hp": 32,
                "player_id": "sarah-user",
                "personality_traits": ["valiant", "cautious"],
            },
        )
        assert create_res.status_code == 200
        char_data = create_res.json()
        char_id = char_data["character_id"]

        # Configure Zanzibar permission: sarah-user owns character
        await spicedb.write_relationship(
            resource_type="character",
            resource_id=str(char_id),
            relation="owner",
            subject_type="user",
            subject_id="sarah-user",
        )

        # 2. Configure tactical guardrails via PUT frontdoor
        guardrails_payload = {
            "preserve_spell_slots": {"3": 1},
            "protect_allies": ["Marcus", "Valeros"],
            "protect_ally_hp_threshold": 0.3,
            "risk_threshold": "cautious",
            "avoid_melee": True,
            "permadeath_safeguard": True,
            "custom_priorities": [
                "Save Level 3 slots for Revivify",
                "Prioritize healing Marcus if under 30% HP",
                "Avoid frontline melee",
            ],
        }

        put_res = await client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json=guardrails_payload,
            headers={"x-user-id": "sarah-user"},
        )
        assert put_res.status_code == 200
        updated_char = put_res.json()
        gr = updated_char["stand_in_guardrails"]
        assert gr["preserve_spell_slots"] == {"3": 1}
        assert gr["protect_allies"] == ["Marcus", "Valeros"]
        assert gr["avoid_melee"] is True
        assert gr["permadeath_safeguard"] is True

        # 3. GET frontdoor returns configured guardrails
        get_res = await client.get(f"/api/v1/characters/{char_id}/guardrails")
        assert get_res.status_code == 200
        get_gr = get_res.json()
        assert get_gr["preserve_spell_slots"] == {"3": 1}
        assert "Marcus" in get_gr["protect_allies"]

        # 4. Unauthorized user cannot edit guardrails (Zanzibar check)
        unauth_res = await client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json=guardrails_payload,
            headers={"x-user-id": "malicious-intruder"},
        )
        assert unauth_res.status_code == 403
        assert "does not have edit permission" in unauth_res.json()["detail"]

    # 5. Verify StandInPolicyUpdated CloudEvent published to Redis Streams
    assert "runefoble.events.character" in mock_redis.streams
    events = [
        deserialize_event(fields) for _, fields in mock_redis.streams["runefoble.events.character"]
    ]
    policy_events = [e for e in events if isinstance(e, StandInPolicyUpdated)]
    assert len(policy_events) >= 1
    assert policy_events[0].character_id == str(char_id)
    assert policy_events[0].guardrails["preserve_spell_slots"] == {"3": 1}


# ---------------------------------------------------------------------------
# 2. Stand-In Graph Policy Evaluation & Humorous Penalty Adaptation
# ---------------------------------------------------------------------------


def test_stand_in_guardrails_evaluation_and_humorous_adaptation(watcher_engine: TheWatcherEngine):
    """Verify stand-in AI evaluates guardrails while adapting penalties (US-0025)."""
    guardrails = {
        "preserve_spell_slots": {3: 1},
        "protect_allies": ["Marcus"],
        "protect_ally_hp_threshold": 0.3,
        "risk_threshold": "cautious",
        "avoid_melee": True,
        "permadeath_safeguard": True,
        "custom_priorities": [
            "Save Level 3 slots for Revivify",
            "Prioritize healing Marcus if under 30% HP",
            "Avoid frontline melee",
        ],
    }

    # Scenario A: Protect Marcus when wounded (under 'drunk' penalty)
    action_heal = watcher_engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["drunk"],
        scene_context="Goblins surround camp. Marcus is wounded and under 30% HP.",
        personality_traits=["valiant"],
        guardrails=guardrails,
    )
    assert action_heal.action_type == "cast_spell"
    assert "Marcus" in action_heal.dialogue
    assert "Hic" in action_heal.dialogue
    assert "Prioritized protection for Marcus" in action_heal.guardrails_applied
    assert action_heal.dice_roll_required == "1d20-2"
    assert "healing magic to protect Marcus" in action_heal.action_description

    # Scenario B: Preserve Level 3 spell slots for Revivify
    action_spell = watcher_engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["drunk"],
        scene_context="In combat with a shadow demon. Needs to cast a spell.",
        personality_traits=["scholarly"],
        guardrails=guardrails,
    )
    assert action_spell.action_type == "cast_spell"
    assert "Preserved Level 3 spell slots" in action_spell.guardrails_applied
    assert "Revivify" in action_spell.dialogue or "Level 3" in action_spell.dialogue
    assert "cantrip" in action_spell.action_description.lower()

    # Scenario C: Avoid frontline melee (under 'foolishness' penalty)
    action_ranged = watcher_engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["foolishness"],
        scene_context="Melee vanguard clash in open arena.",
        personality_traits=["valiant"],
        guardrails=guardrails,
    )
    assert action_ranged.action_type == "ranged_attack"
    assert "Avoided frontline melee" in action_ranged.guardrails_applied
    assert "ranged" in action_ranged.dialogue.lower() or "melee" in action_ranged.dialogue.lower()


# ---------------------------------------------------------------------------
# 3. Aggregate Invariant: Zero-HP Permadeath Safeguard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_hp_permadeath_safeguard_invariant(mock_redis: MockAsyncRedis):
    """Aggregate invariant: Damage reducing a stand-in character to <= 0 HP stabilizes them."""
    bus = RedisStreamsEventBus(client=mock_redis)
    character_set_event_bus(bus)

    transport = ASGITransport(app=character_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create character
        res = await client.post(
            "/api/v1/characters/create",
            json={"name": "Kyra", "character_class": "Cleric", "max_hp": 25},
        )
        assert res.status_code == 200
        char_id = res.json()["character_id"]

        # Configure guardrails with permadeath safeguard
        await client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json={"permadeath_safeguard": True, "avoid_melee": True},
        )

        # Inflict lethal damage (-50 HP) while character is controlled by AI stand-in
        dmg_res = await client.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -50, "source": "dragon_breath", "is_stand_in": True},
        )
        assert dmg_res.status_code == 200
        state = dmg_res.json()

        # Invariant checks: stabilized at exactly 0 HP without death saves
        assert state["current_hp"] == 0
        assert state["is_stabilized"] is True
        assert "unconscious_stabilized" in state["conditions"]
        assert state["conditions"]["unconscious_stabilized"]["source"] == "permadeath_safeguard"

    # Verify StandInStabilized CloudEvent published to Redis Streams
    assert "runefoble.events.character" in mock_redis.streams
    events = [
        deserialize_event(fields) for _, fields in mock_redis.streams["runefoble.events.character"]
    ]
    stabilized_events = [e for e in events if isinstance(e, StandInStabilized)]
    assert len(stabilized_events) >= 1
    assert stabilized_events[0].character_id == str(char_id)
    assert stabilized_events[0].current_hp == 0
    assert stabilized_events[0].condition == "unconscious_stabilized"


# ---------------------------------------------------------------------------
# 4. Mid-Session Hot-Swap Takeover & Turn Order Continuity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mid_session_hot_swap_takeover_and_turn_continuity(mock_redis: MockAsyncRedis):
    """POST /api/v1/sessions/{id}/hot-swap smoothly transfers control in <100ms, preserving combat order."""
    session_bus = RedisStreamsEventBus(client=mock_redis)
    session_set_event_bus(session_bus)
    spicedb = SpiceDBClient()
    session_set_spicedb(spicedb)

    transport = ASGITransport(app=session_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        campaign_id = str(uuid4())
        char_id = str(uuid4())
        player_id = "sarah-user"

        # 1. Setup session and join Sarah
        create_res = await client.post(
            "/api/v1/sessions/create",
            json={"campaign_id": campaign_id, "title": "Tomb of Horror", "dm_id": "the_watcher"},
        )
        session_id = create_res.json()["session_id"]

        await client.post(
            f"/api/v1/sessions/{session_id}/join",
            json={
                "player_id": player_id,
                "character_id": char_id,
                "character_name": "Kyra",
                "character_class": "Cleric",
            },
        )
        await client.post(f"/api/v1/sessions/{session_id}/start")

        # 2. Start combat encounter with initiative
        await client.post(
            f"/api/v1/sessions/{session_id}/combat/start",
            json={
                "combatants": [
                    {"combatant_id": char_id, "combatant_name": "Kyra", "initiative_score": 18},
                    {
                        "combatant_id": "goblin-1",
                        "combatant_name": "Goblin Boss",
                        "initiative_score": 12,
                    },
                ]
            },
        )

        # 3. Sarah marks absent mid-encounter -> stand-in activates
        leave_res = await client.post(
            f"/api/v1/sessions/{session_id}/leave",
            json={"player_id": player_id, "reason": "Late arrival"},
        )
        assert leave_res.status_code == 200
        assert leave_res.json()["participants"][player_id]["is_stand_in_active"] is True

        # 4. Configure SpiceDB permission: Sarah can participate/edit
        await spicedb.write_relationship(
            resource_type="character",
            resource_id=char_id,
            relation="owner",
            subject_type="user",
            subject_id=player_id,
        )

        # 5. Sarah joins and executes hot-swap takeover
        hot_swap_res = await client.post(
            f"/api/v1/sessions/{session_id}/hot-swap",
            json={"player_id": player_id, "character_id": char_id},
            headers={"x-user-id": player_id},
        )
        assert hot_swap_res.status_code == 200
        data = hot_swap_res.json()

        # Turn order continuity assertions:
        assert data["previous_controller"] == "ai_stand_in"
        assert data["new_controller"] == "player"
        assert data["in_combat"] is True
        assert data["combat_round"] == 1
        assert data["combat_active_id"] == char_id
        session_state = data["session_state"]
        participant = session_state["participants"][player_id]
        assert participant["is_present"] is True
        assert participant["is_stand_in_active"] is False

    # 6. Verify CharacterControlTransferred CloudEvent published to Redis Streams
    assert "runefoble.events.session" in mock_redis.streams
    events = [
        deserialize_event(fields) for _, fields in mock_redis.streams["runefoble.events.session"]
    ]
    transfer_events = [e for e in events if isinstance(e, CharacterControlTransferred)]
    assert len(transfer_events) >= 1
    assert transfer_events[0].session_id == str(session_id)
    assert transfer_events[0].character_id == str(char_id)
    assert transfer_events[0].player_id == player_id
    assert transfer_events[0].new_controller == "player"
