"""Blackbox TDD test suite for Watcher Domain Events Modular Decomposition (TASK-0182).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 80 lines for facade, < 150 lines for submodules)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import runefoble_events.watcher as watcher_facade
import runefoble_events.watcher_events as watcher_pkg
from runefoble_events.board_traps import TrapSprungEvent
from runefoble_events.combat_reactions import (
    CombatTurnPausedForReactionEvent,
    ReactionResolvedEvent,
)
from runefoble_events.vocal_dsp import VocalModulatorPresetAppliedEvent
from runefoble_events.watcher_events import (
    actions as actions_mod,
)
from runefoble_events.watcher_events import (
    combat as combat_mod,
)
from runefoble_events.watcher_events import (
    factions as factions_mod,
)
from runefoble_events.watcher_events import (
    narrative as narrative_mod,
)
from runefoble_platform.consumer_group import deserialize_event

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_file_length_invariants():
    """Verify watcher.py and all watcher_events submodules adhere strictly to line limits."""
    events_dir = REPO_ROOT / "libs" / "runefoble_events" / "src" / "runefoble_events"
    facade_path = events_dir / "watcher.py"
    submodules_dir = events_dir / "watcher_events"

    assert facade_path.is_file(), "watcher.py must exist"
    facade_lines = len(facade_path.read_text(encoding="utf-8").splitlines())
    assert facade_lines < 80, (
        f"watcher.py facade ({facade_lines} lines) must be strictly < 80 lines"
    )

    submodule_files = list(submodules_dir.glob("*.py"))
    assert len(submodule_files) >= 5, "watcher_events must contain submodules and __init__.py"

    for path in submodule_files:
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count < 150, f"{path.name} ({line_count} lines) must be strictly < 150 lines"


def test_watcher_facade_backward_compatibility_reexports():
    """Verify all domain events remain importable from runefoble_events.watcher."""
    expected_symbols = [
        "AbsenteeRecapGenerated",
        "AutonomousActionResolved",
        "CandidateGhostPreviewEmitted",
        "CompoundActionResolved",
        "DMNarrativeWhispered",
        "DiceRollEvent",
        "DiceRolled",
        "EncounterSpawned",
        "FactionAgendaAdvanced",
        "FactionAgendaSet",
        "FactionCreated",
        "GeopoliticalShiftOccurred",
        "IntentDisambiguationRequested",
        "PlayerSpokeEvent",
        "ReactionOpportunityResolved",
        "ReactionPromptTriggered",
        "SceneAtmosphereSet",
        "SecretTrapTriggered",
        "SpeechIntentParsed",
        "StandInActionDecided",
        "StandInTurnExecuted",
        "VocalModulatorPresetChanged",
        "VoiceAudioConditioned",
        "WatcherActionApproved",
        "WatcherActionModified",
        "WatcherActionProposed",
        "WatcherActionVetoed",
        "WatcherNarrationEvent",
        "WatcherNarrationGenerated",
        "WorldTickExecuted",
    ]

    for sym in expected_symbols:
        assert hasattr(watcher_facade, sym), f"runefoble_events.watcher must re-export {sym}"
        facade_obj = getattr(watcher_facade, sym)
        pkg_obj = getattr(watcher_pkg, sym)
        assert facade_obj is pkg_obj, f"{sym} in watcher facade must match watcher_events"


def test_submodule_modular_imports():
    """Verify events can be cleanly imported from their focused submodules."""
    assert hasattr(narrative_mod, "PlayerSpokeEvent")
    assert hasattr(narrative_mod, "SpeechIntentParsed")
    assert hasattr(narrative_mod, "WatcherNarrationGenerated")
    assert hasattr(narrative_mod, "StandInActionDecided")

    assert hasattr(combat_mod, "DiceRolled")
    assert hasattr(combat_mod, "ReactionPromptTriggered")
    assert hasattr(combat_mod, "ReactionOpportunityResolved")
    assert hasattr(combat_mod, "SecretTrapTriggered")
    assert hasattr(combat_mod, "VocalModulatorPresetChanged")

    assert hasattr(actions_mod, "WatcherActionProposed")
    assert hasattr(actions_mod, "IntentDisambiguationRequested")
    assert hasattr(actions_mod, "CompoundActionResolved")

    assert hasattr(factions_mod, "FactionCreated")
    assert hasattr(factions_mod, "FactionAgendaAdvanced")
    assert hasattr(factions_mod, "WorldTickExecuted")


def test_reaction_and_trap_events_inheritance():
    """Verify combat reaction, secret trap, and vocal preset events inherit properly."""
    assert issubclass(combat_mod.ReactionPromptTriggered, CombatTurnPausedForReactionEvent)
    assert issubclass(combat_mod.ReactionOpportunityResolved, ReactionResolvedEvent)
    assert issubclass(combat_mod.SecretTrapTriggered, TrapSprungEvent)
    assert issubclass(combat_mod.VocalModulatorPresetChanged, VocalModulatorPresetAppliedEvent)


def test_dice_rolled_properties_and_alias():
    """Verify DiceRolled properties and DiceRollEvent alias work correctly."""
    roll = combat_mod.DiceRolled(
        session_id=str(uuid4()),
        roller_id="player-1",
        roller_name="Aria",
        formula="2d6+3",
        total=11,
        rolls=[5, 3],
        is_crit=False,
    )
    assert roll.dice_notation == "2d6+3"
    assert roll.individual_rolls == [5, 3]
    assert combat_mod.DiceRollEvent is combat_mod.DiceRolled


def test_event_cloudevent_and_serialization_roundtrip():
    """Verify serialization, deserialization, and CloudEvent compliance for decomposed events."""
    session_id = str(uuid4())

    events_to_test = [
        narrative_mod.PlayerSpokeEvent(
            aggregate_id=uuid4(),
            speaker_id="p-1",
            speaker_name="Aria",
            transcript="I inspect the altar",
        ),
        narrative_mod.WatcherNarrationGenerated(
            aggregate_id=uuid4(),
            narrative_text="A cold draft chills the chamber.",
            tone="eerie",
        ),
        combat_mod.DiceRolled(
            session_id=session_id,
            roller_id="p-1",
            roller_name="Aria",
            formula="1d20+5",
            total=18,
            rolls=[13],
        ),
        combat_mod.ReactionPromptTriggered(
            session_id=session_id,
            reacting_combatant_id="comb-1",
            reacting_combatant_name="Aria",
            trigger_phrase="Goblin moves in range",
        ),
        combat_mod.ReactionOpportunityResolved(
            session_id=session_id,
            reacting_combatant_id="comb-1",
            action_taken="opportunity_attack",
        ),
        combat_mod.SecretTrapTriggered(
            board_id="board-1",
            token_id="token-1",
            x=4,
            y=5,
        ),
        combat_mod.VocalModulatorPresetChanged(
            session_id=session_id,
            peer_id="peer-dm",
            preset_name="dragon_bellow",
        ),
        actions_mod.WatcherActionProposed(
            action_id="act-1",
            session_id=session_id,
            actor_name="The Watcher",
            action_type="spawn_monster",
            description="Spawn shadowy phantom",
        ),
        factions_mod.FactionCreated(
            campaign_id="camp-1",
            faction_id="fac-iron-hand",
            name="Iron Hand Guild",
        ),
        factions_mod.WorldTickExecuted(
            campaign_id="camp-1",
            tick_number=3,
            intelligence_bulletin="Tensions rise between guilds.",
        ),
    ]

    for event in events_to_test:
        # 1. CloudEvent dictionary conversion
        ce_dict = event.to_cloudevent_dict()
        assert ce_dict["specversion"] == "1.0"
        assert "data" in ce_dict
        assert ce_dict["id"] == str(event.event_id)

        # 2. Redis Bus serialization & deserialization roundtrip
        message_fields = {
            "event_type": event.event_type,
            "payload": event.model_dump_json(),
        }
        deserialized = deserialize_event(message_fields)
        assert (
            isinstance(deserialized, type(event))
            or event.__class__.__name__ == type(deserialized).__name__
        )
        assert deserialized.event_id == event.event_id
