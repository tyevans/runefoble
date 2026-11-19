"""Blackbox tests for the local stand-in engine's guardrail enforcement and names (TASK-0691).

Each guardrail is set through the public Watcher route. Every reported name must come from the
GuardrailName enumeration, which both engines share.
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_platform.stand_in_guardrails import GuardrailName

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

ACT_PATH = "/api/v1/watcher/stand-in/act"
ENUMERATION = {member.value for member in GuardrailName}


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


async def _act(mock_redis: MockAsyncRedis, use_redis_client, **overrides) -> dict:
    """Send a stand-in act request through the public route and return the JSON body."""
    use_redis_client(mock_redis)
    session_id, campaign_id = str(uuid4()), str(uuid4())
    await make_table_runner("test-user", session_id, campaign_id)
    payload = {
        "character_name": "Kyra",
        "character_class": "Cleric",
        "penalties": [],
        "scene_context": "Goblins press the camp",
        "personality_traits": ["valiant"],
        "guardrails": None,
        "session_id": session_id,
        "campaign_id": campaign_id,
    }
    payload.update(overrides)
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    ) as client:
        resp = await client.post(ACT_PATH, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_local_engine_reports_preserve_spell_slots_by_name(mock_redis, use_redis_client):
    body = await _act(
        mock_redis,
        use_redis_client,
        scene_context="A shadow demon attacks. Cast a spell now.",
        guardrails={"preserve_spell_slots": {"3": 1}},
    )

    assert body["action_type"] == "cast_spell"
    assert body["guardrails_applied"] == ["preserve_spell_slots"]


@pytest.mark.asyncio
async def test_local_engine_reports_protect_allies_by_name(mock_redis, use_redis_client):
    body = await _act(
        mock_redis,
        use_redis_client,
        scene_context="Marcus is wounded by goblins.",
        guardrails={"protect_allies": ["Marcus"]},
    )

    assert body["guardrails_applied"] == ["protect_allies"]


@pytest.mark.asyncio
async def test_local_engine_follows_the_first_priority_named_in_the_scene(
    mock_redis, use_redis_client
):
    body = await _act(
        mock_redis,
        use_redis_client,
        character_class="Fighter",
        scene_context="The Orc Chieftain is at the gate.",
        guardrails={"custom_priorities": ["Orc Chieftain"]},
    )

    assert body["action_type"] == "attack"
    assert "Orc Chieftain" in body["action_description"]
    assert body["guardrails_applied"] == ["custom_priorities"]


@pytest.mark.asyncio
async def test_local_engine_reports_avoid_melee_by_name(mock_redis, use_redis_client):
    body = await _act(
        mock_redis,
        use_redis_client,
        character_class="Wizard",
        scene_context="Frontline clash in the corridor.",
        guardrails={"avoid_melee": True},
    )

    assert body["action_type"] == "ranged_attack"
    assert body["guardrails_applied"] == ["avoid_melee"]


@pytest.mark.asyncio
async def test_local_engine_names_come_from_the_enumeration(mock_redis, use_redis_client):
    body = await _act(
        mock_redis,
        use_redis_client,
        scene_context="Marcus is wounded. Cast a spell now.",
        guardrails={"protect_allies": ["Marcus"], "preserve_spell_slots": {"3": 1}},
    )

    assert set(body["guardrails_applied"]) <= ENUMERATION
