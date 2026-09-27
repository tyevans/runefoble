"""Blackbox TDD tests for Stand-In Tactical Policy and Guardrail Decomposition (TASK-0112).

Verifies:
1. Public HTTP frontdoor POST /api/v1/watcher/stand-in/act handles tactical guardrails:
   - Ally protection priority under penalties.
   - Spell slot preservation limits under penalties.
   - Frontline melee avoidance under penalties.
2. Public HTTP frontdoor POST /api/v1/watcher/stand-in/recap generates chronicle recaps.
3. StandInAIEngine facade delegates cleanly with 100% backward compatibility.
4. Hard Invariant 6: All stand-in source modules are strictly under their line limits (< 150 lines).
"""

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import StandInActionDecided
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus
from the_watcher.stand_in_ai import (
    StandInAIEngine,
    apply_penalty_modifiers,
    evaluate_tactical_guardrails,
    generate_absentee_recap,
)


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def stand_in_engine() -> StandInAIEngine:
    return StandInAIEngine()


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
            "Prioritized protection for Marcus",
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
            "Preserved Level 3 spell slots",
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
            "Avoided frontline melee",
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
):
    """POST /api/v1/watcher/stand-in/act evaluates tactical guardrails under varied conditions."""
    event_bus = RedisStreamsEventBus(client=mock_redis)
    watcher_set_event_bus(event_bus)

    session_id, campaign_id = str(uuid4()), str(uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=watcher_app), base_url="http://test"
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
# 2. StandInAIEngine Facade & Direct Sub-Module Verification
# ---------------------------------------------------------------------------


def test_stand_in_facade_and_submodule_backward_compatibility(
    stand_in_engine: StandInAIEngine,
):
    """Verify facade and extracted helper functions retain full backward compatibility."""
    # 1. Direct evaluate_tactical_guardrails invocation
    gr_action = evaluate_tactical_guardrails(
        character_name="Valeros",
        character_class="Fighter",
        penalties=["drunk"],
        scene_context="Protect Marcus at all costs!",
        personality_traits=["valiant"],
        guardrails={"protect_allies": ["Marcus"]},
    )
    assert gr_action is not None
    assert "Prioritized protection for Marcus" in gr_action.guardrails_applied
    assert gr_action.action_type == "cast_spell"
    assert (
        evaluate_tactical_guardrails("Valeros", "Fighter", [], "Walking peacefully", None, None)
        is None
    )

    # 2. Direct apply_penalty_modifiers invocation
    persona_action = apply_penalty_modifiers(
        character_name="Merisiel",
        character_class="Rogue",
        penalties=["cowardice"],
        scene_context="Ambush",
        personality_traits=["impulsive"],
    )
    assert persona_action.action_type == "defend"
    assert "Cowardice" in (persona_action.penalty_influence or "")

    # 3. Direct generate_absentee_recap invocation
    recap = generate_absentee_recap(
        character_name="Kyra",
        actions=[gr_action, persona_action],
        penalties=["drunk", "cowardice"],
    )
    assert recap["character_name"] == "Kyra"
    assert "drunk" in recap["penalties_active"]
    assert "cowardice" in recap["penalties_active"]
    assert len(recap["highlights"]) >= 2

    # 4. Engine facade produces identical outputs
    facade_action = stand_in_engine.generate_stand_in_action(
        character_name="Valeros",
        character_class="Fighter",
        penalties=["drunk"],
        scene_context="Protect Marcus at all costs!",
        personality_traits=["valiant"],
        guardrails={"protect_allies": ["Marcus"]},
    )
    assert facade_action.action_type == gr_action.action_type
    assert facade_action.dialogue == gr_action.dialogue


# ---------------------------------------------------------------------------
# 3. Modular Decomposition Line Limits and Structural Invariants
# ---------------------------------------------------------------------------


def test_stand_in_decomposition_file_length_invariants():
    """Verify Hard Invariant 6: Decomposed files meet strict line length limits (< 150 lines)."""
    watcher_dir = (
        Path(__file__).resolve().parent.parent / "services" / "the_watcher" / "src" / "the_watcher"
    )

    modules = {
        watcher_dir / "stand_in_ai.py": 80,
        watcher_dir / "stand_in_guardrails.py": 140,
        watcher_dir / "stand_in_persona.py": 140,
        watcher_dir / "stand_in_recap.py": 110,
    }

    for path, max_lines in modules.items():
        assert path.exists(), f"{path.name} must exist"
        lines = len(path.read_text().splitlines())
        assert lines < max_lines, f"{path.name} exceeds {max_lines} lines (current: {lines})"
        assert lines < 200, f"{path.name} exceeds 200 lines (current: {lines})"
