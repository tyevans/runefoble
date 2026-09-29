"""BoardState aggregate and spatial grid events facade."""

# ruff: noqa: F401

from runefoble_events import board_events
from runefoble_events.board_events import (
    AoETemplatePlaced,
    AoETemplateRemoved,
    AreaEffectExploded,
    BoardDoorToggled,
    BoardDoorToggledEvent,
    BoardGridInitialized,
    BoardLightSourcePlaced,
    BoardLightSourcePlacedEvent,
    BoardMapImported,
    BoardMoveEvent,
    DiceSettled,
    ElevationChanged,
    EphemeralDecalsDecayed,
    FogOfWarRevealed,
    FogOfWarShrouded,
    FogRevealed,
    PhysicsCollisionOccurred,
    ShroudReset,
    SpellCast,
    TerrainCellModified,
    TokenActionExecuted,
    TokenHazardTriggered,
    TokenKnockbackApplied,
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
    UniversalVTTImported,
    VFXAnimationFinished,
    VisibilityMaskUpdated,
)

__all__ = list(board_events.__all__)
