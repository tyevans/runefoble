"""BoardState aggregate and spatial grid events."""

from typing import ClassVar, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class BoardGridInitialized(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    width: int = 20
    height: int = 20
    cell_size_px: int = 40
    grid_type: Literal["square", "hex"] = "square"
    session_id_str: str = ""


@register_event
class TokenPlaced(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    token_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"]
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False


@register_event
class TokenMoved(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    token_id: str
    name: str
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"


@register_event
class TokenRemoved(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    token_id: str
    reason: str = "defeated"


@register_event
class FogOfWarRevealed(BaseRunefobleEvent):
    aggregate_type: str = "BoardState"
    revealed_cells: list[list[int]] = Field(default_factory=list)
    revealed_by_token_id: str | None = None


@register_event("runefoble.events.board.terrain_modified")
class TerrainCellModified(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.terrain_modified"
    session_id: str
    board_id: str
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None


@register_event("runefoble.events.board.hazard_triggered")
class TokenHazardTriggered(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.hazard_triggered"
    session_id: str
    board_id: str
    token_id: str
    hazard_type: str
    damage_dice: str


# Legacy backward-compatible alias
BoardMoveEvent = TokenMoved
