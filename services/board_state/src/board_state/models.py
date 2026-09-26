"""Pydantic request and response models for Board State microservice."""

from __future__ import annotations

from typing import Literal

from board_state.aggregate import PlacedTokenState
from pydantic import BaseModel


class CreateBoardRequest(BaseModel):
    session_id: str | None = None
    board_id: str | None = None
    cols: int | None = None
    rows: int | None = None
    width: int | None = None
    height: int | None = None


class ConfigureTerrainRequest(BaseModel):
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None


class PlaceTokenRequest(BaseModel):
    token_id: str | None = None
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = True
    vision_radius: int = 2


class MoveTokenRequest(BaseModel):
    token_id: str | None = None
    to_x: int
    to_y: int
    initiated_by: Literal["player", "the_watcher", "stand_in"] = "player"
    movement_budget: int | None = None


class MoveTokenResponse(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"] = "pc"
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


class VisibilityResponse(BaseModel):
    session_id: str
    cols: int
    rows: int
    fog_of_war_enabled: bool
    revealed_cells: list[list[int]]
    currently_visible_cells: list[list[int]]
    tokens: list[PlacedTokenState]


class FogOfWarUpdateRequest(BaseModel):
    cells: list[list[int]]
    token_id: str | None = None
