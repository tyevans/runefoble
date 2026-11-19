"""Blackbox TDD test suite for Soundscape Event Handlers Modular Decomposition (TASK-0181).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 180 lines for dependencies & event_handlers)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from runefoble_events.events import (
    CharacterHealthChanged,
    CombatEncounterStarted,
    DiceRolled,
    InitiativeTurnAdvanced,
    PlayerSpokeEvent,
)
from runefoble_platform.models import utc_now
from soundscape.event_handlers import handle_incoming_domain_event
from soundscape.leitmotif import LeitmotifEngine
from soundscape.session_state import read_session_state


async def _state(session_id: str):
    """Read the stored soundscape state for a session. The aggregate is the only source."""
    return await read_session_state(session_id)


async def _engine(session_id: str) -> LeitmotifEngine:
    """Rebuild the leitmotif view from the stored state, as the routes do."""
    return LeitmotifEngine.from_state(session_id, await _state(session_id), utc_now())


@pytest.mark.asyncio
async def test_combat_started_event_updates_tension_and_stems():
    """Verify CombatEncounterStarted triggers tension update and combat stem switch."""
    session_id = "session-test-combat-start"
    event = CombatEncounterStarted(
        aggregate_id=uuid4(),
        session_id=session_id,
        round_number=1,
        combatants=[{"name": "Orc Warrior", "cr": 2.0}],
    )
    await handle_incoming_domain_event(event)

    state = await _state(session_id)
    assert state.stem_profile in ("tension", "combat")
    assert state.tension_score == 55


@pytest.mark.asyncio
async def test_initiative_advanced_recalculates_tension():
    """Verify InitiativeTurnAdvanced recalculates encounter tension."""
    session_id = "session-test-initiative"
    event = InitiativeTurnAdvanced(
        aggregate_id=uuid4(),
        session_id=session_id,
        round_number=2,
        active_combatant_id="comb-orc-1",
    )
    await handle_incoming_domain_event(event)

    state = await _state(session_id)
    assert state.stem_profile in ("tension", "combat")


@pytest.mark.asyncio
async def test_player_spoke_triggers_voice_ducking():
    """Verify PlayerSpokeEvent engages WebAudio -12dB ducking in the aggregate state."""
    session_uuid = uuid4()
    session_id = str(session_uuid)
    event = PlayerSpokeEvent(
        aggregate_id=uuid4(),
        session_id=session_uuid,
        speaker_id="player-1",
        speaker_name="Evelyn",
        transcript="Cover the flank!",
    )
    await handle_incoming_domain_event(event)

    state = await _state(session_id)
    assert state.is_ducked_at(utc_now()) is True
    assert state.ducking_attenuation_db == -12.0
    engine = await _engine(session_id)
    assert engine.is_ducked is True


@pytest.mark.asyncio
async def test_critical_hit_triggers_triumphant_leitmotif():
    """Verify a natural 20 (DiceRolled with is_crit) triggers triumphant leitmotif playback."""
    session_id = "session-test-crit"
    event = DiceRolled(
        session_id=session_id,
        roller_id="char-valeros",
        roller_name="Valeros",
        formula="1d20",
        total=20,
        rolls=[20],
        is_crit=True,
    )
    await handle_incoming_domain_event(event)

    engine = await _engine(session_id)
    active = engine.get_active_status()
    assert active is not None
    assert active.motif_type == "triumphant"
    assert active.character_id == "char-valeros"


@pytest.mark.asyncio
async def test_zero_hp_triggers_somber_leitmotif():
    """Verify a health change to 0 HP triggers the somber death-save leitmotif."""
    session_id = "session-test-death"
    character_uuid = uuid4()
    event = CharacterHealthChanged(
        aggregate_id=character_uuid,
        session_id=session_id,
        delta=-12,
        current_hp=0,
        max_hp=12,
    )
    await handle_incoming_domain_event(event)

    engine = await _engine(session_id)
    active = engine.get_active_status()
    assert active is not None
    assert active.motif_type == "somber"
    assert active.character_id == str(character_uuid)
