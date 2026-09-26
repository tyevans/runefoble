"""Blackbox TDD tests for Stand-In Policy Guardrails and Tactical Constraints (TASK-0096, TASK-0055)."""

import pytest
from character_sheet.main import app as character_app
from character_sheet.main import set_event_bus as character_set_event_bus
from character_sheet.main import set_spicedb_client as character_set_spicedb
from httpx import ASGITransport, AsyncClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.events import StandInPolicyUpdated, StandInStabilized
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from the_watcher.watcher_ai import TheWatcherEngine

GUARDRAILS_PAYLOAD = {
    "preserve_spell_slots": {"3": 1},
    "protect_allies": ["Marcus", "Valeros"],
    "protect_ally_hp_threshold": 0.3,
    "risk_threshold": "cautious",
    "avoid_melee": True,
    "permadeath_safeguard": True,
    "custom_priorities": ["Save Level 3 slots for Revivify", "Protect Marcus", "Avoid melee"],
}


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def watcher_engine() -> TheWatcherEngine:
    return TheWatcherEngine()


# --- 1. Character Tactical Guardrails & Zanzibar Authorization ---


@pytest.mark.asyncio
async def test_character_guardrails_configuration_and_events(mock_redis: MockAsyncRedis):
    """PUT /api/v1/characters/{id}/guardrails configures tactical constraints and emits event."""
    bus = RedisStreamsEventBus(client=mock_redis)
    character_set_event_bus(bus)
    spicedb = SpiceDBClient()
    character_set_spicedb(spicedb)

    async with AsyncClient(
        transport=ASGITransport(app=character_app), base_url="http://test"
    ) as client:
        # 1. Create Sarah's Cleric & configure Zanzibar ownership
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
        char_id = create_res.json()["character_id"]
        await spicedb.write_relationship(
            resource_type="character",
            resource_id=str(char_id),
            relation="owner",
            subject_type="user",
            subject_id="sarah-user",
        )

        # 2. Configure tactical guardrails via PUT frontdoor
        put_res = await client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json=GUARDRAILS_PAYLOAD,
            headers={"x-user-id": "sarah-user"},
        )
        assert put_res.status_code == 200
        gr = put_res.json()["stand_in_guardrails"]
        assert gr["preserve_spell_slots"] == {"3": 1}
        assert gr["protect_allies"] == ["Marcus", "Valeros"]
        assert gr["avoid_melee"] is True and gr["permadeath_safeguard"] is True

        # 3. GET frontdoor returns configured guardrails
        get_res = await client.get(f"/api/v1/characters/{char_id}/guardrails")
        assert get_res.status_code == 200 and get_res.json()["preserve_spell_slots"] == {"3": 1}
        assert "Marcus" in get_res.json()["protect_allies"]

        # 4. Unauthorized user cannot edit guardrails (Zanzibar check)
        unauth_res = await client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json=GUARDRAILS_PAYLOAD,
            headers={"x-user-id": "malicious-intruder"},
        )
        assert unauth_res.status_code == 403
        assert "does not have edit permission" in unauth_res.json()["detail"]

    # 5. Verify StandInPolicyUpdated CloudEvent published to Redis Streams
    assert "runefoble.events.character" in mock_redis.streams
    events = [deserialize_event(f) for _, f in mock_redis.streams["runefoble.events.character"]]
    policy_events = [e for e in events if isinstance(e, StandInPolicyUpdated)]
    assert len(policy_events) >= 1 and policy_events[0].character_id == str(char_id)
    assert policy_events[0].guardrails["preserve_spell_slots"] == {"3": 1}


# --- 2. Stand-In Graph Policy Evaluation & Humorous Penalty Adaptation ---


def test_stand_in_guardrails_evaluation_and_humorous_adaptation(watcher_engine: TheWatcherEngine):
    """Verify stand-in AI evaluates guardrails while adapting penalties (US-0025)."""
    gr = {**GUARDRAILS_PAYLOAD, "preserve_spell_slots": {3: 1}}

    # Scenario A: Protect Marcus when wounded (under 'drunk' penalty)
    action_heal = watcher_engine.generate_stand_in_action(
        character_name="Kyra",
        character_class="Cleric",
        penalties=["drunk"],
        scene_context="Goblins surround camp. Marcus is wounded and under 30% HP.",
        personality_traits=["valiant"],
        guardrails=gr,
    )
    assert action_heal.action_type == "cast_spell"
    assert "Marcus" in action_heal.dialogue and "Hic" in action_heal.dialogue
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
        guardrails=gr,
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
        guardrails=gr,
    )
    assert action_ranged.action_type == "ranged_attack"
    assert "Avoided frontline melee" in action_ranged.guardrails_applied
    assert "ranged" in action_ranged.dialogue.lower() or "melee" in action_ranged.dialogue.lower()


# --- 3. Aggregate Invariant: Zero-HP Permadeath Safeguard ---


@pytest.mark.asyncio
async def test_zero_hp_permadeath_safeguard_invariant(mock_redis: MockAsyncRedis):
    """Aggregate invariant: Damage reducing a stand-in character to <= 0 HP stabilizes them."""
    bus = RedisStreamsEventBus(client=mock_redis)
    character_set_event_bus(bus)

    async with AsyncClient(
        transport=ASGITransport(app=character_app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/api/v1/characters/create",
            json={"name": "Kyra", "character_class": "Cleric", "max_hp": 25},
        )
        assert res.status_code == 200
        char_id = res.json()["character_id"]

        await client.put(
            f"/api/v1/characters/{char_id}/guardrails",
            json={"permadeath_safeguard": True, "avoid_melee": True},
        )
        dmg_res = await client.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -50, "source": "dragon_breath", "is_stand_in": True},
        )
        assert dmg_res.status_code == 200
        state = dmg_res.json()
        assert state["current_hp"] == 0 and state["is_stabilized"] is True
        assert state["conditions"]["unconscious_stabilized"]["source"] == "permadeath_safeguard"

    assert "runefoble.events.character" in mock_redis.streams
    events = [deserialize_event(f) for _, f in mock_redis.streams["runefoble.events.character"]]
    stabilized = [e for e in events if isinstance(e, StandInStabilized)]
    assert len(stabilized) >= 1 and stabilized[0].character_id == str(char_id)
    assert stabilized[0].current_hp == 0 and stabilized[0].condition == "unconscious_stabilized"
