"""Blackbox TDD tests for Stand-In Policy Guardrails and Tactical Constraints (TASK-0096, TASK-0055)."""

import pytest
from character_sheet.main import app as character_app
from httpx import ASGITransport, AsyncClient
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_events.events import StandInPolicyUpdated, StandInStabilized
from runefoble_platform.event_deserializer import deserialize_event

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer

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


# --- 1. Character Tactical Guardrails & Zanzibar Authorization ---


@pytest.mark.asyncio
async def test_character_guardrails_configuration_and_events(
    mock_redis: MockAsyncRedis, use_redis_client, spicedb: MockSpiceDBClient
):
    """PUT /api/v1/characters/{id}/guardrails configures tactical constraints and emits event."""
    use_redis_client(mock_redis)

    async with AsyncClient(
        transport=ASGITransport(app=character_app),
        base_url="http://test",
        headers=bearer("character-owner"),
    ) as client:
        # 1. Create Sarah's Cleric & configure Zanzibar ownership
        create_res = await client.post(
            "/api/v1/characters",
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
            headers=bearer("sarah-user"),
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
            headers=bearer("malicious-intruder"),
        )
        assert unauth_res.status_code == 403
        assert unauth_res.json()["detail"]["error"] == "permission_denied"

    # 5. Verify StandInPolicyUpdated CloudEvent published to Redis Streams
    assert "runefoble.events.character" in mock_redis.streams
    events = [deserialize_event(f) for _, f in mock_redis.streams["runefoble.events.character"]]
    policy_events = [e for e in events if isinstance(e, StandInPolicyUpdated)]
    assert len(policy_events) >= 1 and policy_events[0].character_id == str(char_id)
    assert policy_events[0].guardrails["preserve_spell_slots"] == {"3": 1}


# --- 3. Aggregate Invariant: Zero-HP Permadeath Safeguard ---


@pytest.mark.asyncio
async def test_zero_hp_permadeath_safeguard_invariant(mock_redis: MockAsyncRedis, use_redis_client):
    """Aggregate invariant: Damage reducing a stand-in character to <= 0 HP stabilizes them."""
    use_redis_client(mock_redis)

    async with AsyncClient(
        transport=ASGITransport(app=character_app),
        base_url="http://test",
        headers=bearer("character-owner"),
    ) as client:
        res = await client.post(
            "/api/v1/characters",
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
