"""Dynamic point lights and interactive door domain events."""

from typing import Any, ClassVar, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("BoardDoorToggledEvent")
@register_event("runefoble.events.board.door_toggled")
class BoardDoorToggledEvent(BaseRunefobleEvent):
    """Emitted when an interactive door or portal changes state (open/closed/locked)."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.door_toggled"
    board_id: str = ""
    session_id: str = ""
    door_id: str = ""
    status: Literal["open", "closed", "locked"] = "open"
    is_open: bool = True
    toggled_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("BoardLightSourcePlacedEvent")
@register_event("runefoble.events.board.light_source_placed")
class BoardLightSourcePlacedEvent(BaseRunefobleEvent):
    """Emitted when a point light source or radiance emitter is placed on the board."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.light_source_placed"
    board_id: str = ""
    session_id: str = ""
    light_id: str = ""
    x: float = 0.0
    y: float = 0.0
    color_hex: str = "#ffffffff"
    bright_radius: float = 2.5
    dim_radius: float = 5.0
    flicker_intensity: float = 0.0
    intensity: float = 1.0
    shadows: bool = True
    placed_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


BoardDoorToggled = BoardDoorToggledEvent
BoardLightSourcePlaced = BoardLightSourcePlacedEvent

__all__ = [
    "BoardDoorToggled",
    "BoardDoorToggledEvent",
    "BoardLightSourcePlaced",
    "BoardLightSourcePlacedEvent",
]
