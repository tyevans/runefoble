"""Domain events for Universal VTT interactive doors and dynamic point lights."""

from __future__ import annotations

from runefoble_events.board_events.lighting import (
    BoardDoorToggled,
    BoardDoorToggledEvent,
    BoardLightSourcePlaced,
    BoardLightSourcePlacedEvent,
)

__all__ = [
    "BoardDoorToggled",
    "BoardDoorToggledEvent",
    "BoardLightSourcePlaced",
    "BoardLightSourcePlacedEvent",
]
