"""BoardState domain events package."""

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

__all__ = [
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
