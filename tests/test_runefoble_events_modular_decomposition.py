"""Blackbox tests verifying modular decomposition and backward compatibility of runefoble_events.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 500 lines, submodules < 150 lines, facades < 80 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- TASK-0177: Runefoble Events Aggregator Modular Decomposition
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import runefoble_events
import runefoble_events.events as events_pkg
from runefoble_events.base import BaseRunefobleEvent, register_event
from runefoble_events.board_events import (
    BoardGridInitialized as BoardGridRoot,
)
from runefoble_events.board_events import (
    TokenMoved as TokenMovedRoot,
)
from runefoble_events.events.board_events import (
    AoETemplatePlaced,
    BoardGridInitialized,
    FogOfWarRevealed,
    TokenMoved,
    TrapSprung,
)
from runefoble_events.events.character_events import (
    CharacterCreated,
    CharacterDamaged,
    ItemAddedToInventory,
)
from runefoble_events.events.media_events import (
    BattlemapForged,
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
    ChronicleMilestoneRecorded,
    DynamicToolRegistered,
    MercenaryBountyPosted,
)
from runefoble_events.events.session_events import (
    CombatEncounterStarted,
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
    SettlementChartered,
)
from runefoble_events.narrative_events import (
    DiceRolled as DiceRolledRoot,
)
from runefoble_events.narrative_events import (
    WatcherNarrationGenerated as WatcherNarrationRoot,
)
from runefoble_events.session_events import (
    CombatEncounterStarted as CombatEncounterRoot,
)
from runefoble_events.session_events import (
    SessionCreated as SessionCreatedRoot,
)
from runefoble_events.world_events import (
    CaravanDispatched as CaravanDispatchedRoot,
)
from runefoble_events.world_events import (
    FactionCreated as FactionCreatedRoot,
)


def test_aggregator_facade_and_submodule_file_length_invariants() -> None:
    """Verify strictly enforced file length budgets per TASK-0177 and Hard Invariant 6."""
    pkg_dir = (
        Path(__file__).resolve().parent.parent
        / "libs"
        / "runefoble_events"
        / "src"
        / "runefoble_events"
    )
    events_dir = pkg_dir / "events"

    # Facade budget targets (< 80 lines)
    assert len((pkg_dir / "events.py").read_text(encoding="utf-8").splitlines()) < 80
    assert len((pkg_dir / "__init__.py").read_text(encoding="utf-8").splitlines()) < 80
    assert len((events_dir / "__init__.py").read_text(encoding="utf-8").splitlines()) < 80

    # Category submodule budgets specified in TASK-0177
    submodule_budgets = {
        "session_events.py": 100,
        "board_events.py": 110,
        "narrative_events.py": 100,
        "world_events.py": 110,
        "character_events.py": 150,
        "media_events.py": 150,
        "platform_events.py": 150,
    }

    for filename, max_lines in submodule_budgets.items():
        file_path = events_dir / filename
        assert file_path.exists(), f"Missing expected submodule: {filename}"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{filename} has {lines} lines, exceeding budget {max_lines}"
        assert lines < 150, f"{filename} violates Hard Invariant 6 (< 150 lines)"

    # Backwards-compatibility aliases in package root (< 150 lines)
    for filename in submodule_budgets:
        alias_path = pkg_dir / filename
        assert alias_path.exists(), f"Missing expected alias file: {filename}"
        lines = len(alias_path.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"Alias {filename} exceeds limit: {lines} lines"

    # Global Hard Invariant 6: No file in runefoble_events exceeds 500 lines
    for p in pkg_dir.rglob("*.py"):
        line_count = len(p.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"{p.name} has {line_count} lines, breaching 500 line limit"


def test_backward_compatibility_re_export_parity() -> None:
    """Verify that all domain events are accessible from top-level and category modules identically."""
    # Frontdoor package root re-exports
    assert runefoble_events.SessionCreated is SessionCreated
    assert runefoble_events.TokenMoved is TokenMoved
    assert runefoble_events.WatcherNarrationGenerated is WatcherNarrationGenerated
    assert runefoble_events.FactionCreated is FactionCreated
    assert runefoble_events.CharacterCreated is CharacterCreated
    assert runefoble_events.BattlemapForged is BattlemapForged
    assert runefoble_events.ChronicleMilestoneRecorded is ChronicleMilestoneRecorded

    # Facade events package re-exports
    assert events_pkg.SessionCreated is SessionCreated
    assert events_pkg.TokenMoved is TokenMoved
    assert events_pkg.WatcherNarrationGenerated is WatcherNarrationGenerated
    assert events_pkg.CaravanDispatched is CaravanDispatched
    assert events_pkg.register_event is register_event

    # Root alias module parity
    assert SessionCreatedRoot is SessionCreated
    assert CombatEncounterRoot is CombatEncounterStarted
    assert TokenMovedRoot is TokenMoved
    assert BoardGridRoot is BoardGridInitialized
    assert WatcherNarrationRoot is WatcherNarrationGenerated
    assert DiceRolledRoot is DiceRolled
    assert FactionCreatedRoot is FactionCreated
    assert CaravanDispatchedRoot is CaravanDispatched


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
    assert TrapSprung is not None

    # Narrative category
    assert WatcherNarrationGenerated is not None
    assert SpeechIntentParsed is not None
    assert StandInActionDecided is not None
    assert AbsenteeRecapGenerated is not None
    assert DiceRolled is not None

    # World category
    assert FactionCreated is not None
    assert CaravanDispatched is not None
    assert SettlementChartered is not None
    assert LoreDocumentIngested is not None
    assert AliasesConsolidated is not None

    # Character & Platform categories
    assert CharacterDamaged is not None
    assert ItemAddedToInventory is not None
    assert SoundscapeTrackChanged is not None
    assert VoicePeerJoined is not None
    assert DynamicToolRegistered is not None
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
    """Verify complete __all__ contents across events facade and root package."""
    assert len(runefoble_events.__all__) >= 210
    assert len(events_pkg.__all__) >= 210

    # Ensure all symbols listed in __all__ are resolvable attributes
    for symbol_name in events_pkg.__all__:
        assert hasattr(events_pkg, symbol_name), f"Attribute {symbol_name} missing from events"
        assert hasattr(runefoble_events, symbol_name), (
            f"Attribute {symbol_name} missing from runefoble_events"
        )
