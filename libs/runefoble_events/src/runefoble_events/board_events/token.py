"""Tactile token kinematics, placement, action, and knockback domain events."""

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.board.token_placed")
class TokenPlaced(BaseRunefobleEvent):
    event_type: str = "runefoble.events.board.token_placed"

    aggregate_type: str = "BoardState"
    token_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle", "loot"]
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False


@register_event("runefoble.events.board.token_moved")
class TokenMoved(BaseRunefobleEvent):
    event_type: str = "runefoble.events.board.token_moved"

    aggregate_type: str = "BoardState"
    token_id: str
    name: str
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"


@register_event("runefoble.events.board.token_removed")
class TokenRemoved(BaseRunefobleEvent):
    event_type: str = "runefoble.events.board.token_removed"

    aggregate_type: str = "BoardState"
    token_id: str
    reason: str = "defeated"


@register_event("runefoble.events.board.token_action_executed")
class TokenActionExecuted(BaseRunefobleEvent):
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
