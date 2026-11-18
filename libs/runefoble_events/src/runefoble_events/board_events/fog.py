"""Fog-of-war visibility, shroud reset, and line-of-sight domain events."""

from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.board.fog_of_war_revealed")
class FogOfWarRevealed(BaseRunefobleEvent):
    event_type: str = "runefoble.events.board.fog_of_war_revealed"

    aggregate_type: str = "BoardState"
    revealed_cells: list[list[int]] = Field(default_factory=list)
    revealed_by_token_id: str | None = None


@register_event("runefoble.events.board.fog_of_war_shrouded")
class FogOfWarShrouded(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.fog_of_war_shrouded"
    session_id: str = ""
    shrouded_cells: list[list[int]] = Field(default_factory=list)
