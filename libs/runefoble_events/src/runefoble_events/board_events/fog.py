"""Fog-of-war visibility, shroud reset, and line-of-sight domain events."""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class FogOfWarRevealed(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    revealed_cells: list[list[int]] = Field(default_factory=list)
    revealed_by_token_id: str | None = None


FogRevealed = FogOfWarRevealed
register_event(FogOfWarRevealed, event_type="FogRevealed")


@register_event("runefoble.events.board.fog_of_war_shrouded")
class FogOfWarShrouded(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.fog_of_war_shrouded"
    session_id: str = ""
    shrouded_cells: list[list[int]] = Field(default_factory=list)


ShroudReset = FogOfWarShrouded
register_event(FogOfWarShrouded, event_type="ShroudReset")
register_event(FogOfWarShrouded, event_type="FogOfWarShrouded")


@register_event("runefoble.events.board.visibility_mask_updated")
class VisibilityMaskUpdated(BaseRunefobleEvent):
    """Emitted when the complete visibility mask or line-of-sight polygon is updated."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.visibility_mask_updated"
    session_id: str = ""
    board_id: str = ""
    token_id: str | None = None
    revealed_count: int = 0
    total_cells: int = 0


register_event(VisibilityMaskUpdated, event_type="VisibilityMaskUpdated")
