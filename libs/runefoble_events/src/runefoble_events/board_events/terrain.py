"""Board grid initialization, terrain cell modification, and VTT import events."""

from typing import Any, ClassVar, Literal
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


@register_event("runefoble.events.board.map_imported")
class UniversalVTTImported(BaseRunefobleEvent):
    """Emitted when a Universal VTT (.dd2vtt) battlemap is imported onto the board."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.map_imported"
    session_id: str = ""
    cols: int
    rows: int
    pixels_per_grid: int = 70
    background_asset_id: str | None = None
    background_image_url: str | None = None
    wall_segments: list[dict[str, Any]] = Field(default_factory=list)
    portals: list[dict[str, Any]] = Field(default_factory=list)
    doors: dict[str, Any] = Field(default_factory=dict)
    lights: list[dict[str, Any]] = Field(default_factory=list)


BoardMapImported = UniversalVTTImported
register_event(UniversalVTTImported, event_type="BoardMapImported")
register_event(UniversalVTTImported, event_type="UniversalVTTImported")
