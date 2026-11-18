"""Blackbox tests for soundscape tension inputs derived from encounter and health events (TASK-0618).

Governed by:
- ADR-0006: Redis Streams domain event streaming
- ADR-0014: BDD and blackbox frontdoor tests
- Hard Invariant 7: setup goes through published domain events, assertions read the tension route
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_events.character import CharacterHealthChanged
from runefoble_events.session import CombatEncounterStarted, CombatRoundAdvanced
from soundscape.event_handlers import handle_incoming_domain_event
from soundscape.main import app

from tests.helpers.ws_identity import SIGNING_ISSUER


def _client() -> TestClient:
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('soundscape-tester')}"}
    return TestClient(app, headers=headers)


def _read_tension(session_id: str) -> dict:
    response = _client().get(f"/api/v1/soundscape/tension?session_id={session_id}")
    assert response.status_code == 200, response.text
    return response.json()


def _combat_start(session_id: str, combatants: list[dict]) -> CombatEncounterStarted:
    return CombatEncounterStarted(
        aggregate_id=uuid4(),
        session_id=session_id,
        round_number=1,
        combatants=combatants,
    )


EZREN = uuid4()
MERISIEL = uuid4()


def _health(session_id: str, character: UUID, current_hp: int, max_hp: int = 10):
    """Publish-shaped CharacterHealthChanged. The character is the aggregate id."""
    return CharacterHealthChanged(
        aggregate_id=character,
        session_id=session_id,
        delta=0,
        current_hp=current_hp,
        max_hp=max_hp,
    )


@pytest.mark.asyncio
async def test_low_party_health_in_combat_raises_tension_and_healing_lowers_it_again():
    """A character at 10% HP raises tension. Healing the character restores the score."""
    session_id = f"session-{uuid4().hex[:8]}"
    await handle_incoming_domain_event(
        _combat_start(session_id, [{"combatant_id": "orc-1", "name": "Orc", "cr": 2.0}])
    )
    await handle_incoming_domain_event(_health(session_id, EZREN, current_hp=10))
    await handle_incoming_domain_event(_health(session_id, MERISIEL, current_hp=10))
    assert _read_tension(session_id)["tension_score"] == 55

    await handle_incoming_domain_event(_health(session_id, MERISIEL, current_hp=1))
    low = _read_tension(session_id)
    assert low["tension_score"] == 92
    assert low["stem_profile"] == "boss"

    await handle_incoming_domain_event(_health(session_id, MERISIEL, current_hp=10))
    assert _read_tension(session_id)["tension_score"] == 55


@pytest.mark.asyncio
async def test_health_change_outside_combat_leaves_ambient_tension_unchanged():
    """Ambient exploration ignores party health. The score stays at the ambient floor."""
    session_id = f"session-{uuid4().hex[:8]}"
    await handle_incoming_domain_event(_health(session_id, EZREN, current_hp=1))

    assert _read_tension(session_id)["tension_score"] == 10


@pytest.mark.asyncio
async def test_combat_start_derives_enemy_cr_from_combatants():
    """Enemy CR comes from the combatant roster. Fractions such as 1/4 are read as numbers."""
    session_id = f"session-{uuid4().hex[:8]}"
    await handle_incoming_domain_event(
        _combat_start(
            session_id,
            [
                {"combatant_id": "gob-1", "name": "Goblin", "cr": "1/4"},
                {"combatant_id": "orc-1", "name": "Orc", "cr": "2"},
                {"combatant_id": "bandit-1", "name": "Bandit"},
            ],
        )
    )

    # 40 base + 5 round + int(2.25 * 5) = 11 CR threat, with full health.
    assert _read_tension(session_id)["tension_score"] == 56


@pytest.mark.asyncio
async def test_round_advance_reuses_encounter_cr_from_combat_start():
    """A later round keeps the CR from the encounter roster. It does not use a fixed constant."""
    session_id = f"session-{uuid4().hex[:8]}"
    await handle_incoming_domain_event(
        _combat_start(session_id, [{"combatant_id": "orc-1", "name": "Orc", "cr": 2.0}])
    )
    await handle_incoming_domain_event(
        CombatRoundAdvanced(aggregate_id=uuid4(), session_id=session_id, round_number=3)
    )

    # 40 base + 15 round + 10 CR threat, with full health. A constant 2.5 would give 67.
    tension = _read_tension(session_id)
    assert tension["tension_score"] == 65
    assert tension["stem_profile"] == "combat"
