"""Placed token state and token placement/movement schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from pydantic import BaseModel


class PlacedTokenState(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle", "loot"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False
    vision_radius: int = 2
    active_hazard: str | None = None
    hazard_status: str | None = None
    active_action: str | None = None
    # The character of a character token, so a client finds its own token (TASK-0945).
    character_id: str | None = None

    @classmethod
    def from_placed_event(cls, event: Any, hazard: str | None = None) -> PlacedTokenState:
        return cls(
            token_id=str(event.token_id),
            name=event.name,
            token_type=event.token_type,
            x=event.x,
            y=event.y,
            hp=event.hp,
            is_friendly=event.is_friendly,
            character_id=event.character_id,
            active_hazard=hazard,
            hazard_status="active" if hazard else None,
        )


class PlaceTokenRequest(BaseModel):
    token_id: str | None = None
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle", "loot"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = True
    vision_radius: int = 2
    character_id: str | None = None


class MoveTokenRequest(BaseModel):
    token_id: str | None = None
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"
    movement_budget: int | None = None


class MoveTokenResponse(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle", "loot"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False
    vision_radius: int = 2
    active_hazard: str | None = None
    hazard_status: str | None = None
    movement_cost: int = 1
    hazard_triggered: str | None = None
    damage_dice: str | None = None
    trap_triggered: str | None = None
    movement_paused: bool = False


@dataclass(frozen=True)
class MoveOutcome:
    """The result of one token move. HTTP and WebSocket moves send these same fields."""

    movement_cost: int
    hazard_triggered: str | None = None
    damage_dice: str | None = None
    trap_triggered: str | None = None
    movement_paused: bool = False

    def as_wire(self) -> dict[str, Any]:
        """Return the move fields for a response body or a socket frame."""
        return asdict(self)
