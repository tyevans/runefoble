"""Blackbox tests verifying modular decomposition of runefoble_events.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 500 lines, submodules < 150 lines, facades < 80 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- TASK-0177: Runefoble Events Aggregator Modular Decomposition
"""

from __future__ import annotations

from uuid import uuid4

import runefoble_events
import runefoble_events.events as events_pkg
from runefoble_events.base import BaseRunefobleEvent
from runefoble_events.events.board_events import (
    AoETemplatePlaced,
    BoardGridInitialized,
    FogOfWarRevealed,
    TokenMoved,
    TrapSprungEvent,
)
from runefoble_events.events.character_events import (
    CharacterDamaged,
    ItemAddedToInventory,
)
from runefoble_events.events.media_events import (
    SoundscapeTrackChanged,
    VoicePeerJoined,
)
from runefoble_events.events.narrative_events import (
    AbsenteeRecapGenerated,
    DiceRolled,
    SpeechIntentParsed,
    StandInActionDecided,
    WatcherNarrationGenerated,
)
from runefoble_events.events.platform_events import (
    DynamicToolRegisteredEvent,
    MercenaryBountyPosted,
)
from runefoble_events.events.session_events import (
    CombatRoundAdvanced,
    GameSessionStarted,
    InitiativeRolled,
    SessionCreated,
    TurnAdvanced,
)
from runefoble_events.events.world_events import (
    AliasesConsolidated,
    CaravanDispatched,
    FactionCreated,
    LoreDocumentIngested,
    SettlementCharteredEvent,
)


def test_category_submodules_exported_symbols() -> None:
    """Verify exported symbols across distinct domain category modules."""
    # Session category
    assert SessionCreated is not None
    assert GameSessionStarted is not None
    assert TurnAdvanced is not None
    assert InitiativeRolled is not None
    assert CombatRoundAdvanced is not None

    # Board category
    assert BoardGridInitialized is not None
    assert TokenMoved is not None
    assert FogOfWarRevealed is not None
    assert AoETemplatePlaced is not None
    assert TrapSprungEvent is not None

    # Narrative category
    assert WatcherNarrationGenerated is not None
    assert SpeechIntentParsed is not None
    assert StandInActionDecided is not None
    assert AbsenteeRecapGenerated is not None
    assert DiceRolled is not None

    # World category
    assert FactionCreated is not None
    assert CaravanDispatched is not None
    assert SettlementCharteredEvent is not None
    assert LoreDocumentIngested is not None
    assert AliasesConsolidated is not None

    # Character & Platform categories
    assert CharacterDamaged is not None
    assert ItemAddedToInventory is not None
    assert SoundscapeTrackChanged is not None
    assert VoicePeerJoined is not None
    assert DynamicToolRegisteredEvent is not None
    assert MercenaryBountyPosted is not None


def test_domain_event_instantiation_and_cloudevent_compliance() -> None:
    """Verify frontdoor creation and CloudEvents attributes for events across categories."""
    aggregate_id = uuid4()
    session_ev = SessionCreated(
        aggregate_id=aggregate_id, session_id="sess-0177", campaign_id="camp-0177"
    )
    assert session_ev.session_id == "sess-0177"
    assert session_ev.aggregate_id == aggregate_id
    assert issubclass(SessionCreated, BaseRunefobleEvent)

    token_ev = TokenMoved(
        aggregate_id=aggregate_id,
        token_id="tok-0177",
        name="Gimli",
        from_x=0,
        from_y=0,
        to_x=5,
        to_y=5,
    )
    assert token_ev.token_id == "tok-0177"
    assert token_ev.to_x == 5

    watcher_ev = WatcherNarrationGenerated(
        aggregate_id=aggregate_id,
        narrative_text="The ancient stone door grinds open.",
    )
    assert "stone door" in watcher_ev.narrative_text

    caravan_ev = CaravanDispatched(
        aggregate_id=uuid4(),
        aggregate_type="CaravanContract",
        caravan_id="car-0177",
        origin_outpost="outpost-alpha",
        destination_outpost="outpost-beta",
    )
    assert caravan_ev.caravan_id == "car-0177"
    assert caravan_ev.aggregate_type == "CaravanContract"


def test_all_public_symbols_registered_and_iterable() -> None:
    """Verify the events aggregator exports every public symbol and the package root exports base types only."""
    assert len(events_pkg.__all__) >= 210
    assert set(runefoble_events.__all__) == {"BaseRunefobleEvent", "DomainEvent", "register_event"}

    # Ensure all symbols listed in __all__ are resolvable attributes
    for symbol_name in events_pkg.__all__:
        assert hasattr(events_pkg, symbol_name), f"Attribute {symbol_name} missing from events"
