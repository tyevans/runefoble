"""Secret DM grid layer, spatial traps, and stage triggers models."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class SecretTrapState(BaseModel):
    """Event-sourced secret spatial trap state on the tactical grid."""

    trap_id: str = Field(default_factory=lambda: f"trap-{uuid4().hex[:8]}")
    board_id: str
    name: str = "Secret Trap"
    x: int
    y: int
    trigger_type: Literal["step", "proximity", "touch"] = "step"
    proximity_radius: int = 1
    dc_detection: int = 15
    trap_type: str = "pit_trap"
    is_secret: bool = True
    is_armed: bool = True
    is_sprung: bool = False
    is_disarmed: bool = False
    damage_dice: str | None = None
    description: str = ""
    effect_payload: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None


class CreateTrapRequest(BaseModel):
    """Request payload to lay a secret DM trap on the board."""

    trap_id: str | None = None
    name: str = "Secret Trap"
    x: int
    y: int
    trigger_type: Literal["step", "proximity", "touch"] = "step"
    proximity_radius: int = 1
    dc_detection: int = 15
    trap_type: str = "pit_trap"
    is_secret: bool = True
    damage_dice: str | None = None
    description: str = ""
    effect_payload: dict[str, Any] = Field(default_factory=dict)


class TrapListResponse(BaseModel):
    """Response containing filtered list of traps visible to the caller."""

    board_id: str
    traps: list[SecretTrapState] = Field(default_factory=list)
    total: int = 0


class SwitchMapRequest(BaseModel):
    """Request to transition to a new battlemap and teleport party tokens."""

    new_map_id: str
    cols: int | None = None
    rows: int | None = None
    background_asset_id: str | None = None
    background_image_url: str | None = None
    token_teleports: dict[str, list[int]] = Field(default_factory=dict)
    clear_existing_traps: bool = False


class SwitchMapResponse(BaseModel):
    """Response from map switch operation with token relocations."""

    board_id: str
    previous_map_id: str | None = None
    new_map_id: str
    cols: int
    rows: int
    background_asset_id: str | None = None
    background_image_url: str | None = None
    teleported_tokens: dict[str, list[int]] = Field(default_factory=dict)
    status: str = "switched"
