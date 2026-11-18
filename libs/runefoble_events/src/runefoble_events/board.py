"""BoardState aggregate and spatial grid events facade."""

# ruff: noqa: F401

from runefoble_events import board_events
from runefoble_events.board_events import (
    AoETemplatePlaced,
    AoETemplateRemoved,
    AreaEffectExploded,
    BoardDoorToggledEvent,
    BoardGridInitialized,
    BoardLightSourcePlacedEvent,
    BoardMapImported,
    BoardMoveEvent,
    DiceSettled,
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
    TokenMoved,
    TokenPlaced,
    TokenRemoved,
    UniversalVTTImported,
    VFXAnimationFinished,
)

__all__ = list(board_events.__all__)
