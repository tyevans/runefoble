"""Tests verifying modular decomposition and backward compatibility of GameSessionAggregate.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines, target < 160 lines per submodule)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.application.aggregates.repository import AggregateRepository
from game_session.aggregate import (
    CombatHandlersMixin,
    GameSessionAggregate,
    GameSessionState,
    ParticipantState,
    ReactionHandlersMixin,
    SessionHandlersMixin,
)
from runefoble_events.events import (
    CharacterControlTransferred,
    CombatEncounterEnded,
    CombatEncounterStarted,
    CombatTurnPausedForReactionEvent,
    InitiativeRolled,
    InitiativeTurnAdvanced,
    PlayerJoinedSession,
    PlayerLeftSession,
    ReactionResolvedEvent,
    ReadyActionRegisteredEvent,
    ReadyActionTriggeredEvent,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    StandInActionDecided,
    TurnAdvanced,
)


def test_package_facade_and_backward_compatibility() -> None:
    """Verify that GameSessionAggregate and related classes are re-exported cleanly."""
    assert GameSessionAggregate is not None
    assert GameSessionState is not None
    assert ParticipantState is not None
    assert SessionHandlersMixin is not None
    assert CombatHandlersMixin is not None
    assert ReactionHandlersMixin is not None

    # Verify mixin inheritance hierarchy
    assert issubclass(GameSessionAggregate, SessionHandlersMixin)
    assert issubclass(GameSessionAggregate, CombatHandlersMixin)
    assert issubclass(GameSessionAggregate, ReactionHandlersMixin)


def test_aggregate_submodules_line_count_invariant() -> None:
    """Verify all aggregate modules strictly adhere to the < 160 line count budget."""
    pkg_dir = (
        Path(__file__).resolve().parent.parent
        / "services"
        / "game_session"
        / "src"
        / "game_session"
        / "aggregate"
    )
    facade_file = pkg_dir.parent / "aggregate.py"

    assert facade_file.exists()
    assert len(facade_file.read_text().splitlines()) < 160

    submodules = [
        "__init__.py",
        "aggregate.py",
        "combat_handlers.py",
        "reaction_handlers.py",
        "session_handlers.py",
    ]
    for sub in submodules:
        sub_file = pkg_dir / sub
        assert sub_file.exists(), f"Submodule file {sub_file} does not exist"
        lines = len(sub_file.read_text().splitlines())
        assert lines < 160, f"{sub} has {lines} lines, exceeding 160 line limit"


def test_event_handlers_registry_completeness() -> None:
    """Verify all expected domain events are registered on GameSessionAggregate."""
    registered_events = set(GameSessionAggregate._event_handlers.keys())
    expected_events = {
        SessionCreated,
        SessionStarted,
        PlayerJoinedSession,
        PlayerLeftSession,
        CharacterControlTransferred,
        TurnAdvanced,
        StandInActionDecided,
        SessionEnded,
        CombatEncounterStarted,
        InitiativeRolled,
        InitiativeTurnAdvanced,
        CombatEncounterEnded,
        CombatTurnPausedForReactionEvent,
        ReactionResolvedEvent,
        ReadyActionRegisteredEvent,
        ReadyActionTriggeredEvent,
    }
    missing = expected_events - registered_events
    assert not missing, f"Missing registered event handlers for: {missing}"


@pytest.mark.asyncio
async def test_full_aggregate_domain_lifecycle_and_reconstitution() -> None:
    """Verify full domain lifecycle and event reconstitution across session, combat, and reaction mixins."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=GameSessionAggregate)

    session_id = uuid4()
    campaign_id = uuid4()
    char_id = uuid4()

    # 1. Session Lifecycle (SessionHandlersMixin)
    session = GameSessionAggregate(session_id)
    session.create(campaign_id=campaign_id, title="Caverns of Peril", dm_id="dm_watcher")
    assert session.state.status == "lobby"
    assert session.state.title == "Caverns of Peril"

    session.join_player("player_1", char_id, "Thorin", "Fighter")
    assert "player_1" in session.state.participants

    session.start()
    assert session.state.status == "active"
    assert session.state.current_turn == 1

    session.leave_player("player_1", reason="Connection lost")
    assert session.state.participants["player_1"].is_stand_in_active is True

    session.hot_swap_character("player_1", char_id)
    assert session.state.participants["player_1"].is_stand_in_active is False

    # 2. Combat & Initiative (CombatHandlersMixin)
    goblin_id = "token_goblin_1"
    session.start_combat([{"combatant_id": goblin_id, "combatant_name": "Goblin", "is_npc": True}])
    assert session.state.in_combat is True
    assert session.state.combat_round == 1

    session.roll_initiative(goblin_id, "Goblin", 14, is_npc=True)
    session.roll_initiative(str(char_id), "Thorin", 18, is_npc=False)
    assert session.state.combat_active_id == str(char_id)

    session.advance_initiative()
    assert session.state.combat_active_id == goblin_id

    # 3. Spoken Reactions & Ready Actions (ReactionHandlersMixin)
    reaction_id = "react_shield_001"
    session.declare_reaction(
        reaction_id=reaction_id,
        reacting_combatant_id=str(char_id),
        reacting_combatant_name="Thorin",
        trigger_phrase="I raise my shield!",
        reaction_type="shield_block",
        timeout_seconds=10.0,
        details={"ac_bonus": 2},
    )
    assert session.state.turn_paused_for_reaction is True
    assert session.state.active_reaction is not None
    assert session.state.active_reaction["reaction_id"] == reaction_id

    session.resolve_reaction(reaction_id=reaction_id, action_taken="executed", resumed=True)
    assert session.state.turn_paused_for_reaction is False
    assert session.state.active_reaction is None

    ready_id = "ready_overwatch_001"
    session.register_ready_action(
        ready_action_id=ready_id,
        combatant_id=str(char_id),
        combatant_name="Thorin",
        trigger_type="approaches_within_range",
        trigger_condition="goblin moves within 5ft",
        target_id=goblin_id,
        range_cells=1,
        readied_action="melee_strike",
    )
    assert len(session.state.ready_actions) == 1

    session.trigger_ready_action(
        ready_action_id=ready_id,
        combatant_id=str(char_id),
        combatant_name="Thorin",
        triggering_entity_id=goblin_id,
        trigger_type="approaches_within_range",
        readied_action="melee_strike",
    )
    assert len(session.state.ready_actions) == 0

    session.end_combat()
    assert session.state.in_combat is False

    # 4. Turn Advancement, Stand-In Action, & Session End (aggregate.py)
    session.advance_turn()
    assert session.state.current_turn == 2

    session.record_stand_in_action(
        character_name="Thorin",
        action_type="defend",
        dialogue="Hold the line!",
        penalties_applied=["foolishness"],
        flavor_text="Strikes a defensive stance.",
    )
    assert len(session.state.stand_in_actions) == 1

    session.end("Adventure completed")
    assert session.state.status == "ended"

    # 5. Persist to event store and reload to verify replay reconstitution
    await repo.save(session)

    reconstituted = await repo.load(session_id)
    assert reconstituted.version == session.version
    assert reconstituted.state.status == "ended"
    assert reconstituted.state.current_turn == 2
    assert len(reconstituted.state.stand_in_actions) == 1
    assert reconstituted.state.in_combat is False
