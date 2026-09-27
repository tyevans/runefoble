"""Domain events for secret DM traps, map switching, and stage triggers."""

from __future__ import annotations

from typing import Any, ClassVar, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("TrapPlacedEvent")
@register_event("runefoble.events.board.trap_placed")
class TrapPlacedEvent(BaseRunefobleEvent):
    """Emitted when a secret DM spatial trap or trigger is placed on the board."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.trap_placed"
    trap_id: str = Field(default_factory=lambda: f"trap-{uuid4().hex[:8]}")
    board_id: str = ""
    name: str = "Secret Trap"
    x: int = 0
    y: int = 0
    trigger_type: Literal["step", "proximity", "touch"] = "step"
    proximity_radius: int = 1
    dc_detection: int = 15
    trap_type: str = "pit_trap"
    is_secret: bool = True
    damage_dice: str | None = None
    description: str = ""
    effect_payload: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None


@register_event("TrapSprungEvent")
@register_event("runefoble.events.board.trap_sprung")
class TrapSprungEvent(BaseRunefobleEvent):
    """Emitted when a moving token breaches an armed trap cell or proximity zone."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.trap_sprung"
    trap_id: str = ""
    board_id: str = ""
    token_id: str = ""
    trigger_type: Literal["step", "proximity", "touch"] = "step"
    x: int = 0
    y: int = 0
    damage_dice: str | None = None
    effect_payload: dict[str, Any] = Field(default_factory=dict)
    movement_paused: bool = True


@register_event("TrapDisarmedEvent")
@register_event("runefoble.events.board.trap_disarmed")
class TrapDisarmedEvent(BaseRunefobleEvent):
    """Emitted when a secret trap is disarmed or disabled."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.trap_disarmed"
    trap_id: str = ""
    board_id: str = ""
    disarmed_by: str | None = None


@register_event("BattlemapSwitchedEvent")
@register_event("runefoble.events.board.battlemap_switched")
class BattlemapSwitchedEvent(BaseRunefobleEvent):
    """Emitted when the DM transitions the stage to a new battlemap and teleports tokens."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.battlemap_switched"
    board_id: str = ""
    previous_map_id: str | None = None
    new_map_id: str = ""
    cols: int = 12
    rows: int = 12
    background_asset_id: str | None = None
    background_image_url: str | None = None
    teleported_tokens: dict[str, list[int]] = Field(default_factory=dict)
    initiated_by: str | None = None


# Public domain event aliases
TrapPlaced = TrapPlacedEvent
TrapSprung = TrapSprungEvent
TrapDisarmed = TrapDisarmedEvent
BattlemapSwitched = BattlemapSwitchedEvent

__all__ = [
    "BattlemapSwitched",
    "BattlemapSwitchedEvent",
    "TrapDisarmed",
    "TrapDisarmedEvent",
    "TrapPlaced",
    "TrapPlacedEvent",
    "TrapSprung",
    "TrapSprungEvent",
]
