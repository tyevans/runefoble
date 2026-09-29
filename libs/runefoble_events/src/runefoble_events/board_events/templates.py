"""Geometric AoE spell template positioning and removal domain events."""

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.board.aoe_template_placed")
class AoETemplatePlaced(BaseRunefobleEvent):
    """Emitted when a geometric AoE spell template is positioned on the board."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.aoe_template_placed"
    session_id: str = ""
    board_id: str = ""
    template_id: str = Field(default_factory=lambda: str(uuid4()))
    caster_token_id: str | None = None
    shape: str = "cone"
    origin_x: float
    origin_y: float
    direction_deg: float = 0.0
    radius_ft: float | None = None
    length_ft: float | None = None
    width_ft: float | None = None
    spell_name: str | None = None
    affected_token_ids: list[str] = Field(default_factory=list)
    affected_cells: list[list[int]] = Field(default_factory=list)


@register_event("runefoble.events.board.aoe_template_removed")
class AoETemplateRemoved(BaseRunefobleEvent):
    """Emitted when an active AoE template is removed from the board."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.aoe_template_removed"
    session_id: str = ""
    board_id: str = ""
    template_id: str


register_event(AoETemplatePlaced, event_type="AoETemplatePlaced")
register_event(AoETemplateRemoved, event_type="AoETemplateRemoved")
