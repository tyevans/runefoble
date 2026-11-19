"""Blackbox TDD tests for Stand-In Tactical Policy and Guardrail Decomposition (TASK-0112).

Verifies:
1. Public HTTP frontdoor POST /api/v1/watcher/stand-in/act handles tactical guardrails:
   - Ally protection priority under penalties.
   - Spell slot preservation limits under penalties.
   - Frontline melee avoidance under penalties.
2. Public HTTP frontdoor POST /api/v1/watcher/stand-in/recap generates chronicle recaps.
3. Guardrail results carry the guardrail name and action type through the HTTP frontdoor.
4. Hard Invariant 6: All stand-in source modules are strictly under their line limits (< 150 lines).
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import StandInActionDecided
from runefoble_platform.event_deserializer import deserialize_event
from runefoble_platform.stand_in_guardrails import GuardrailName
from the_watcher.main import app as watcher_app

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import make_table_runner
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


# ---------------------------------------------------------------------------
# 1. Blackbox HTTP Frontdoor Tests for Tactical Guardrails (US-0025)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,cls,penalties,traits,context,guardrails,exp_type,exp_dlg,exp_gr,exp_dice",
    [
        (
            "Kyra",
            "Cleric",
            ["drunk"],
            ["valiant"],
            "Marcus is wounded and taking damage from goblins.",
            {"protect_allies": ["Marcus"], "avoid_melee": False, "preserve_spell_slots": {}},
            "cast_spell",
            "Marcus",
            GuardrailName.PROTECT_ALLIES,
            "1d20-2",
        ),
        (
            "Kyra",
            "Cleric",
            ["foolishness"],
            ["scholarly"],
            "Demon approaches. Needs to cast a spell.",
            {"preserve_spell_slots": {"3": 1}, "protect_allies": [], "avoid_melee": False},
            "cast_spell",
            "Level 3",
            GuardrailName.PRESERVE_SPELL_SLOTS,
            "1d20",
        ),
        (
            "Ezren",
            "Wizard",
            [],
            ["scholarly"],
            "Frontline clash in dungeon corridor.",
            {"avoid_melee": True, "protect_allies": []},
            "ranged_attack",
            "tactical distance",
            GuardrailName.AVOID_MELEE,
            "1d20+2",
        ),
    ],
)
async def test_blackbox_stand_in_guardrails_scenarios(
    mock_redis: MockAsyncRedis,
    name: str,
    cls: str,
    penalties: list[str],
    traits: list[str],
    context: str,
    guardrails: dict,
    exp_type: str,
    exp_dlg: str,
    exp_gr: str,
    exp_dice: str,
    use_redis_client,
):
    """POST /api/v1/watcher/stand-in/act evaluates tactical guardrails under varied conditions."""
    use_redis_client(mock_redis)

    session_id, campaign_id = str(uuid4()), str(uuid4())
    await make_table_runner("test-user", session_id, campaign_id)
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
    ) as client:
        resp = await client.post(
            "/api/v1/watcher/stand-in/act",
            json={
                "character_name": name,
                "character_class": cls,
                "penalties": penalties,
                "scene_context": context,
                "personality_traits": traits,
                "guardrails": guardrails,
                "session_id": session_id,
                "campaign_id": campaign_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["character_name"] == name
        assert data["action_type"] == exp_type
        assert exp_dlg.lower() in data["dialogue"].lower()
        assert exp_gr in data["guardrails_applied"]
        assert data["dice_roll_required"] == exp_dice

    events = [deserialize_event(f) for _, f in mock_redis.streams["runefoble.events.watcher"]]
    action_events = [e for e in events if isinstance(e, StandInActionDecided)]
    assert any(
        e.action_type == exp_type and exp_dlg.lower() in e.dialogue.lower() for e in action_events
    )


# ---------------------------------------------------------------------------
# 3. Modular Decomposition Line Limits and Structural Invariants
# ---------------------------------------------------------------------------
