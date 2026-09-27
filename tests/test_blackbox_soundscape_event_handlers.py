"""Blackbox TDD test suite for Soundscape Event Handlers Modular Decomposition (TASK-0181).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 180 lines for dependencies & event_handlers)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from runefoble_events import (
    CombatEncounterStarted,
    CriticalHitScored,
    DeathSaveStarted,
    DiceRolled,
    InitiativeTurnAdvanced,
    PlayerSpokeEvent,
)
from runefoble_platform.bus import bus as platform_bus
from soundscape.dependencies import (
    get_or_create_aggregate_id,
    get_or_create_leitmotif_engine,
    get_or_create_mixer,
    get_soundscape_repo,
    reset_dependencies,
)
from soundscape.dependencies import (
    handle_incoming_domain_event as deps_handle_event,
)
from soundscape.event_handlers import (
    handle_incoming_domain_event,
    register_soundscape_event_handlers,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean aggregate, mixer, and bus states before and after each test."""
    reset_dependencies()
    yield
    reset_dependencies()


def test_module_line_count_invariants():
    """Verify dependencies.py and event_handlers.py strictly adhere to line length limit (< 180)."""
    soundscape_dir = REPO_ROOT / "services" / "soundscape" / "src" / "soundscape"
    deps_path = soundscape_dir / "dependencies.py"
    handlers_path = soundscape_dir / "event_handlers.py"

    assert deps_path.is_file(), "dependencies.py must exist"
    assert handlers_path.is_file(), "event_handlers.py must exist"

    deps_lines = len(deps_path.read_text(encoding="utf-8").splitlines())
    handlers_lines = len(handlers_path.read_text(encoding="utf-8").splitlines())

    assert deps_lines < 180, f"dependencies.py ({deps_lines} lines) exceeds 180 lines limit"
    assert handlers_lines < 180, (
        f"event_handlers.py ({handlers_lines} lines) exceeds 180 lines limit"
    )


def test_handler_backward_compatibility_reexport():
    """Verify dependencies re-exports handle_incoming_domain_event for compatibility."""
    assert deps_handle_event is handle_incoming_domain_event


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

    mixer = get_or_create_mixer(session_id)
    assert mixer.stem_profile in ("tension", "combat")

    repo = get_soundscape_repo()
    agg_id = get_or_create_aggregate_id(session_id)
    agg = await repo.load(agg_id)
    assert agg is not None
    assert agg.state.tension_score == 55


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

    mixer = get_or_create_mixer(session_id)
    assert mixer.stem_profile in ("tension", "combat")


@pytest.mark.asyncio
async def test_player_spoke_triggers_voice_ducking():
    """Verify PlayerSpokeEvent engages WebAudio -12dB ducking on mixer and leitmotif."""
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

    mixer = get_or_create_mixer(session_id)
    assert mixer.is_ducked is True
    engine = get_or_create_leitmotif_engine(session_id)
    assert engine.is_ducked is True


@pytest.mark.asyncio
async def test_critical_hit_triggers_triumphant_leitmotif():
    """Verify CriticalHitScored triggers triumphant leitmotif playback."""
    session_id = "session-test-crit"
    event = CriticalHitScored(
        session_id=session_id,
        character_id="char-valeros",
        character_name="Valeros",
        roll_total=20,
    )
    await handle_incoming_domain_event(event)

    engine = get_or_create_leitmotif_engine(session_id)
    active = engine.get_active_status()
    assert active is not None
    assert active.motif_type == "triumphant"
    assert active.character_id == "char-valeros"


@pytest.mark.asyncio
async def test_death_save_triggers_somber_leitmotif():
    """Verify DeathSaveStarted triggers somber leitmotif."""
    session_id = "session-test-death"
    event = DeathSaveStarted(
        session_id=session_id,
        character_id="char-merisiel",
        character_name="Merisiel",
        current_hp=0,
    )
    await handle_incoming_domain_event(event)

    engine = get_or_create_leitmotif_engine(session_id)
    active = engine.get_active_status()
    assert active is not None
    assert active.motif_type == "somber"
    assert active.character_id == "char-merisiel"


@pytest.mark.asyncio
async def test_register_soundscape_event_handlers_subscribes_to_platform_bus():
    """Verify register_soundscape_event_handlers wires handlers to platform_bus."""
    register_soundscape_event_handlers()

    session_id = "session-test-bus-sub"
    dice_event = DiceRolled(
        session_id=session_id,
        roller_id="char-ezren",
        roller_name="Ezren",
        formula="1d20+8",
        total=28,
        rolls=[20],
        is_crit=True,
    )
    await platform_bus.publish("DiceRolled", dice_event)

    engine = get_or_create_leitmotif_engine(session_id)
    active = engine.get_active_status()
    assert active is not None
    assert active.motif_type == "triumphant"
    assert active.character_id == "char-ezren"
