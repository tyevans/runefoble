"""BoardState aggregate and spatial grid events."""

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


@register_event("runefoble.events.board.fog_of_war_shrouded")
class FogOfWarShrouded(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.fog_of_war_shrouded"
    session_id: str = ""
    shrouded_cells: list[list[int]] = Field(default_factory=list)


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
    lights: list[dict[str, Any]] = Field(default_factory=list)


# Register backward-compatible aliases
BoardMapImported = UniversalVTTImported
register_event(UniversalVTTImported, event_type="BoardMapImported")
register_event(UniversalVTTImported, event_type="UniversalVTTImported")


@register_event("runefoble.events.board.token_action_executed")
class TokenActionExecuted(BaseRunefobleEvent):
    """Emitted when a tactical token executes a combat action (e.g. Dodge, Dash, Attack)."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.token_action_executed"
    session_id: str = ""
    board_id: str = ""
    token_id: str
    action: str
    target_token_id: str | None = None
    target_token_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    initiated_by: str = "player"


@register_event("runefoble.events.board.aoe_template_placed")
class AoETemplatePlaced(BaseRunefobleEvent):
    """Emitted when a geometric AoE spell template is positioned and confirmed on the board."""

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


register_event(TokenActionExecuted, event_type="TokenActionExecuted")
register_event(AoETemplatePlaced, event_type="AoETemplatePlaced")
register_event(AoETemplateRemoved, event_type="AoETemplateRemoved")

# Legacy backward-compatible alias
BoardMoveEvent = TokenMoved
