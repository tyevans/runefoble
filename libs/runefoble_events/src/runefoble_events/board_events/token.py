"""Tactile token kinematics, placement, action, and knockback domain events."""

from typing import Any, ClassVar, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


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


@register_event("runefoble.events.board.token_action_executed")
class TokenActionExecuted(BaseRunefobleEvent):
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


@register_event("runefoble.events.board.token_knockback_applied")
class TokenKnockbackApplied(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.token_knockback_applied"
    session_id: str = ""
    board_id: str = ""
    token_id: str
    distance_ft: float = 0.0
    direction_x: float = 0.0
    direction_y: float = 0.0
    from_x: int = 0
    from_y: int = 0
    to_x: int = 0
    to_y: int = 0
    mass: float = 1.0


@register_event("runefoble.events.board.elevation_changed")
class ElevationChanged(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.board.elevation_changed"
    session_id: str = ""
    board_id: str = ""
    token_id: str = ""
    previous_elevation: int = 0
    new_elevation: int = 0
    x: int = 0
    y: int = 0


BoardMoveEvent = TokenMoved
register_event(TokenMoved, event_type="BoardMoveEvent")
register_event(TokenActionExecuted, event_type="TokenActionExecuted")
register_event(TokenKnockbackApplied, event_type="TokenKnockbackApplied")
register_event(ElevationChanged, event_type="ElevationChanged")
