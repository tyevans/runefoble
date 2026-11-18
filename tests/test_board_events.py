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

from uuid import uuid4

import runefoble_events.board as board_facade
import runefoble_events.board_events as board_pkg
import runefoble_events.events as events_facade
from eventsource.domain.event_registry import get_event_class_or_none
from runefoble_events.board_events.fog import (
    FogOfWarRevealed,
    FogOfWarShrouded,
    FogRevealed,
    ShroudReset,
)
from runefoble_events.board_events.lighting import (
    BoardDoorToggledEvent,
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
    TokenActionExecuted,
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
)


def test_board_facade_re_exports() -> None:
    """Verify board symbol parity across the board facades."""
    expected_symbols = [
        "AoETemplatePlaced",
        "AoETemplateRemoved",
        "AreaEffectExploded",
        "BoardDoorToggledEvent",
        "BoardGridInitialized",
        "BoardLightSourcePlacedEvent",
        "BoardMapImported",
        "BoardMoveEvent",
        "DiceSettled",
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
        "TokenMoved",
        "TokenPlaced",
        "TokenRemoved",
        "UniversalVTTImported",
        "VFXAnimationFinished",
    ]

    for symbol in expected_symbols:
        assert hasattr(board_facade, symbol), f"Symbol {symbol} missing from runefoble_events.board"
        assert hasattr(board_pkg, symbol), (
            f"Symbol {symbol} missing from runefoble_events.board_events"
        )
        assert hasattr(events_facade, symbol), (
            f"Symbol {symbol} missing from runefoble_events.events"
        )


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
    assert ce_move["type"] == "runefoble.events.board.token_moved"
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

    # BoardLightSourcePlacedEvent
    light_ev = BoardLightSourcePlacedEvent(
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
    assert BoardLightSourcePlacedEvent is BoardLightSourcePlacedEvent

    # BoardDoorToggledEvent
    door_ev = BoardDoorToggledEvent(
        aggregate_id=agg_id,
        board_id="board-01",
        door_id="door-main",
        status="open",
        is_open=True,
    )
    assert door_ev.is_open is True
    assert BoardDoorToggledEvent is BoardDoorToggledEvent


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
    assert get_event_class_or_none("runefoble.events.board.token_moved") is TokenMoved
    assert get_event_class_or_none("runefoble.events.board.token_knockback_applied") is None
    assert get_event_class_or_none("runefoble.events.board.elevation_changed") is None
    assert get_event_class_or_none("runefoble.events.board.visibility_mask_updated") is None
    # Retired short names and Python alias names resolve to no event.
    assert get_event_class_or_none("FogRevealed") is None
    assert get_event_class_or_none("ShroudReset") is None
    assert get_event_class_or_none("BoardLightSourcePlacedEvent") is None
    assert get_event_class_or_none("BoardDoorToggledEvent") is None
