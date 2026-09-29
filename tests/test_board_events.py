"""Blackbox tests verifying board domain events modular decomposition and CloudEvents compliance.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0007: Domain-Driven Design Architecture
- ADR-0013: Modular Decomposition
- Hard Invariant 6: File length limit (< 500 lines, submodules < 120 lines, facade < 50 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
- TASK-0231: Board Domain Events Modular Decomposition
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import runefoble_events
import runefoble_events.board as board_facade
import runefoble_events.board_events as board_pkg
import runefoble_events.events as events_facade
from eventsource.domain.event_registry import get_event_class_or_none
from runefoble_events.board_events.fog import (
    FogOfWarRevealed,
    FogOfWarShrouded,
    FogRevealed,
    ShroudReset,
    VisibilityMaskUpdated,
)
from runefoble_events.board_events.lighting import (
    BoardDoorToggled,
    BoardDoorToggledEvent,
    BoardLightSourcePlaced,
    BoardLightSourcePlacedEvent,
)
from runefoble_events.board_events.physics import (
    DiceSettled,
    PhysicsCollisionOccurred,
)
from runefoble_events.board_events.spells import (
    AreaEffectExploded,
    EphemeralDecalsDecayed,
    SpellCast,
    VFXAnimationFinished,
)
from runefoble_events.board_events.templates import (
    AoETemplatePlaced,
    AoETemplateRemoved,
)
from runefoble_events.board_events.terrain import (
    BoardGridInitialized,
    BoardMapImported,
    TerrainCellModified,
    TokenHazardTriggered,
    UniversalVTTImported,
)
from runefoble_events.board_events.token import (
    BoardMoveEvent,
    ElevationChanged,
    TokenActionExecuted,
    TokenKnockbackApplied,
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
)


def test_board_events_file_length_invariants() -> None:
    """Verify strictly enforced file length budgets per TASK-0231 and Hard Invariant 6."""
    pkg_dir = (
        Path(__file__).resolve().parent.parent
        / "libs"
        / "runefoble_events"
        / "src"
        / "runefoble_events"
    )
    board_events_dir = pkg_dir / "board_events"

    # Facade budget target: strictly < 50 lines (TASK-0231 Definition of Done 1)
    board_facade_lines = len((pkg_dir / "board.py").read_text(encoding="utf-8").splitlines())
    assert board_facade_lines < 50, f"board.py has {board_facade_lines} lines (must be < 50)"

    # Submodule budgets under board_events/ (TASK-0231 Definition of Done 2: strictly < 120 lines)
    submodule_budgets = {
        "token.py": 100,
        "fog.py": 80,
        "templates.py": 80,
        "lighting.py": 80,
        "terrain.py": 80,
        "physics.py": 80,
        "spells.py": 120,
        "__init__.py": 80,
    }

    for filename, max_lines in submodule_budgets.items():
        submodule_path = board_events_dir / filename
        assert submodule_path.exists(), f"Missing expected board submodule: {filename}"
        line_count = len(submodule_path.read_text(encoding="utf-8").splitlines())
        assert line_count < max_lines, (
            f"Submodule {filename} has {line_count} lines, exceeding budget {max_lines}"
        )
        assert line_count < 120, f"Submodule {filename} violates invariant (< 120 lines)"


def test_board_facade_backward_compatibility_re_exports() -> None:
    """Verify 100% backward-compatible symbol parity across board facades."""
    expected_symbols = [
        "AoETemplatePlaced",
        "AoETemplateRemoved",
        "AreaEffectExploded",
        "BoardDoorToggled",
        "BoardDoorToggledEvent",
        "BoardGridInitialized",
        "BoardLightSourcePlaced",
        "BoardLightSourcePlacedEvent",
        "BoardMapImported",
        "BoardMoveEvent",
        "DiceSettled",
        "ElevationChanged",
        "EphemeralDecalsDecayed",
        "FogOfWarRevealed",
        "FogOfWarShrouded",
        "FogRevealed",
        "PhysicsCollisionOccurred",
        "ShroudReset",
        "SpellCast",
        "TerrainCellModified",
        "TokenActionExecuted",
        "TokenHazardTriggered",
        "TokenKnockbackApplied",
        "TokenMoved",
        "TokenPlaced",
        "TokenRemoved",
        "UniversalVTTImported",
        "VFXAnimationFinished",
        "VisibilityMaskUpdated",
    ]

    for symbol in expected_symbols:
        assert hasattr(board_facade, symbol), f"Symbol {symbol} missing from runefoble_events.board"
        assert hasattr(board_pkg, symbol), (
            f"Symbol {symbol} missing from runefoble_events.board_events"
        )
        assert hasattr(events_facade, symbol), (
            f"Symbol {symbol} missing from runefoble_events.events"
        )
        assert hasattr(runefoble_events, symbol), f"Symbol {symbol} missing from runefoble_events"


def test_token_events_instantiation_and_cloudevents() -> None:
    """Verify frontdoor instantiation and serialization for token domain events."""
    agg_id = uuid4()

    # TokenPlaced
    placed_ev = TokenPlaced(
        aggregate_id=agg_id,
        name="Thorin",
        token_type="pc",
        x=1,
        y=1,
        hp=25,
        is_friendly=True,
    )
    assert placed_ev.name == "Thorin"
    assert placed_ev.hp == 25

    # TokenMoved & BoardMoveEvent alias
    move_ev = TokenMoved(
        aggregate_id=agg_id,
        token_id="tok-alpha",
        name="Aria",
        from_x=2,
        from_y=3,
        to_x=4,
        to_y=5,
    )
    assert move_ev.token_id == "tok-alpha"
    assert BoardMoveEvent is TokenMoved
    ce_move = move_ev.to_cloudevent_dict()
    assert ce_move["type"] == "runefoble.tokenmoved"
    assert ce_move["data"]["to_x"] == 4

    # TokenRemoved
    rem_ev = TokenRemoved(
        aggregate_id=agg_id,
        token_id="tok-alpha",
        reason="defeated",
    )
    assert rem_ev.reason == "defeated"

    # TokenActionExecuted
    action_ev = TokenActionExecuted(
        aggregate_id=agg_id,
        token_id="tok-alpha",
        action="dodge",
    )
    assert action_ev.action == "dodge"

    # TokenKnockbackApplied
    kb_ev = TokenKnockbackApplied(
        aggregate_id=agg_id,
        token_id="tok-alpha",
        distance_ft=15.0,
        direction_x=1.0,
        direction_y=0.0,
        from_x=2,
        from_y=3,
        to_x=5,
        to_y=3,
        mass=2.0,
    )
    assert kb_ev.distance_ft == 15.0
    assert kb_ev.mass == 2.0
    ce_kb = kb_ev.to_cloudevent_dict()
    assert ce_kb["type"] == "runefoble.events.board.token_knockback_applied"

    # ElevationChanged
    elev_ev = ElevationChanged(
        aggregate_id=agg_id,
        token_id="tok-alpha",
        previous_elevation=0,
        new_elevation=10,
        x=5,
        y=3,
    )
    assert elev_ev.new_elevation == 10
    ce_elev = elev_ev.to_cloudevent_dict()
    assert ce_elev["type"] == "runefoble.events.board.elevation_changed"


def test_fog_events_instantiation() -> None:
    """Verify fog-of-war reveal, shroud reset, and visibility mask domain events."""
    agg_id = uuid4()

    # FogOfWarRevealed & FogRevealed alias
    fog_ev = FogOfWarRevealed(
        aggregate_id=agg_id,
        revealed_cells=[[1, 1], [1, 2], [2, 1]],
        revealed_by_token_id="tok-alpha",
    )
    assert len(fog_ev.revealed_cells) == 3
    assert FogRevealed is FogOfWarRevealed

    # FogOfWarShrouded & ShroudReset alias
    shroud_ev = FogOfWarShrouded(
        aggregate_id=agg_id,
        session_id="sess-01",
        shrouded_cells=[[5, 5]],
    )
    assert len(shroud_ev.shrouded_cells) == 1
    assert ShroudReset is FogOfWarShrouded

    # VisibilityMaskUpdated
    mask_ev = VisibilityMaskUpdated(
        aggregate_id=agg_id,
        session_id="sess-01",
        board_id="board-01",
        token_id="tok-alpha",
        revealed_count=42,
        total_cells=100,
    )
    assert mask_ev.revealed_count == 42
    ce_mask = mask_ev.to_cloudevent_dict()
    assert ce_mask["type"] == "runefoble.events.board.visibility_mask_updated"


def test_templates_and_lighting_events_instantiation() -> None:
    """Verify AoE template, dynamic lighting, and interactive door event models."""
    agg_id = uuid4()

    # AoETemplatePlaced
    template_ev = AoETemplatePlaced(
        aggregate_id=agg_id,
        shape="cone",
        origin_x=10.0,
        origin_y=10.0,
        direction_deg=45.0,
        radius_ft=30.0,
        spell_name="Burning Hands",
    )
    assert template_ev.shape == "cone"
    assert template_ev.direction_deg == 45.0

    # AoETemplateRemoved
    rem_template_ev = AoETemplateRemoved(
        aggregate_id=agg_id,
        template_id=template_ev.template_id,
    )
    assert rem_template_ev.template_id == template_ev.template_id

    # BoardLightSourcePlaced
    light_ev = BoardLightSourcePlaced(
        aggregate_id=agg_id,
        board_id="board-01",
        light_id="light-torch-1",
        x=5.0,
        y=5.0,
        bright_radius=4.0,
        dim_radius=8.0,
    )
    assert light_ev.light_id == "light-torch-1"
    assert light_ev.bright_radius == 4.0
    assert BoardLightSourcePlaced is BoardLightSourcePlacedEvent

    # BoardDoorToggled
    door_ev = BoardDoorToggled(
        aggregate_id=agg_id,
        board_id="board-01",
        door_id="door-main",
        status="open",
        is_open=True,
    )
    assert door_ev.is_open is True
    assert BoardDoorToggled is BoardDoorToggledEvent


def test_terrain_spells_and_physics_events_instantiation() -> None:
    """Verify terrain, kinetic spell VFX, and 3D collision event models."""
    agg_id = uuid4()

    # BoardGridInitialized
    grid_ev = BoardGridInitialized(
        aggregate_id=agg_id,
        width=30,
        height=30,
        cell_size_px=50,
    )
    assert grid_ev.width == 30

    # TerrainCellModified & TokenHazardTriggered
    terrain_ev = TerrainCellModified(
        aggregate_id=agg_id,
        session_id="sess-01",
        board_id="board-01",
        x=3,
        y=4,
        elevation=2,
        terrain_type="difficult",
    )
    assert terrain_ev.elevation == 2

    hazard_ev = TokenHazardTriggered(
        aggregate_id=agg_id,
        session_id="sess-01",
        board_id="board-01",
        token_id="tok-alpha",
        hazard_type="lava",
        damage_dice="2d10",
    )
    assert hazard_ev.hazard_type == "lava"

    # UniversalVTTImported & BoardMapImported alias
    vtt_ev = UniversalVTTImported(
        aggregate_id=agg_id,
        cols=20,
        rows=20,
    )
    assert vtt_ev.cols == 20
    assert BoardMapImported is UniversalVTTImported

    # Spells & VFX
    spell_ev = SpellCast(
        aggregate_id=agg_id,
        spell_name="Fireball",
        target_x=10,
        target_y=12,
    )
    assert spell_ev.spell_name == "Fireball"

    bloom_ev = AreaEffectExploded(
        aggregate_id=agg_id,
        spell_name="Fireball",
        center_x=10,
        center_y=12,
    )
    assert bloom_ev.center_x == 10

    vfx_ev = VFXAnimationFinished(
        aggregate_id=agg_id,
        animation_id="anim-123",
        spell_name="Fireball",
        target_x=10,
        target_y=12,
    )
    assert vfx_ev.animation_id == "anim-123"

    decal_ev = EphemeralDecalsDecayed(
        aggregate_id=agg_id,
        rounds=1,
    )
    assert decal_ev.rounds == 1

    # Physics collisions & tumbling dice
    collision_ev = PhysicsCollisionOccurred(
        aggregate_id=agg_id,
        entity_id="tok-alpha",
        x=5.0,
        y=5.0,
    )
    assert collision_ev.entity_id == "tok-alpha"

    dice_ev = DiceSettled(
        aggregate_id=agg_id,
        dice_id="dice-d20-1",
        face_value=20,
        settled_x=5.0,
        settled_y=5.0,
    )
    assert dice_ev.face_value == 20


def test_event_registry_resolution() -> None:
    """Verify that domain event types resolve correctly from the global event registry."""
    assert get_event_class_or_none("TokenMoved") is TokenMoved
    assert get_event_class_or_none("BoardMoveEvent") is TokenMoved
    assert (
        get_event_class_or_none("runefoble.events.board.token_knockback_applied")
        is TokenKnockbackApplied
    )
    assert get_event_class_or_none("TokenKnockbackApplied") is TokenKnockbackApplied
    assert get_event_class_or_none("runefoble.events.board.elevation_changed") is ElevationChanged
    assert get_event_class_or_none("ElevationChanged") is ElevationChanged
    assert (
        get_event_class_or_none("runefoble.events.board.visibility_mask_updated")
        is VisibilityMaskUpdated
    )
    assert get_event_class_or_none("VisibilityMaskUpdated") is VisibilityMaskUpdated
    assert get_event_class_or_none("FogRevealed") is FogOfWarRevealed
    assert get_event_class_or_none("ShroudReset") is FogOfWarShrouded
    assert get_event_class_or_none("BoardLightSourcePlacedEvent") is BoardLightSourcePlacedEvent
    assert get_event_class_or_none("BoardDoorToggledEvent") is BoardDoorToggledEvent
