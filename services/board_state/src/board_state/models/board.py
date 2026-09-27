"""Board aggregate state and lifecycle schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from board_state.aoe_models import AoETemplateState
from board_state.models.terrain import TerrainCellState, TerrainDict
from board_state.models.tokens import PlacedTokenState
from board_state.models.transitions import BoardTransitionsMixin
from board_state.models.vfx import BoardDecalState
from pydantic import BaseModel, Field


class BoardState(BaseModel, BoardTransitionsMixin):
    board_id: UUID
    session_id: str = ""
    cols: int = 12
    rows: int = 12
    tokens: dict[str, PlacedTokenState] = Field(default_factory=dict)
    terrain_cells: dict[str, TerrainCellState] = Field(default_factory=TerrainDict)
    active_hazards: list[str] = Field(default_factory=list)
    active_decals: list[BoardDecalState] = Field(default_factory=list)
    fog_of_war_enabled: bool = True
    revealed_cells: list[list[int]] = Field(default_factory=list)
    background_asset_id: str | None = None
    background_image_url: str | None = None
    wall_segments: list[dict[str, Any]] = Field(default_factory=list)
    portals: list[dict[str, Any]] = Field(default_factory=list)
    lights: list[dict[str, Any]] = Field(default_factory=list)
    pixels_per_grid: int = 70
    active_aoe_templates: list[AoETemplateState] = Field(default_factory=list)

    @classmethod
    def initial(cls, board_id: UUID, session_id: str, cols: int, rows: int) -> BoardState:
        return cls(board_id=board_id, session_id=session_id, cols=cols, rows=rows)


class CreateBoardRequest(BaseModel):
    session_id: str | None = None
    board_id: str | None = None
    cols: int | None = None
    rows: int | None = None
    width: int | None = None
    height: int | None = None


class FogOfWarUpdateRequest(BaseModel):
    cells: list[list[int]]
    token_id: str | None = None


class UVTTImportResponse(BaseModel):
    board_id: UUID
    session_id: str = ""
    cols: int
    rows: int
    pixels_per_grid: int = 70
    wall_segments: list[dict[str, Any]] = Field(default_factory=list)
    portals: list[dict[str, Any]] = Field(default_factory=list)
    lights: list[dict[str, Any]] = Field(default_factory=list)
    background_image_url: str | None = None
    background_asset_id: str | None = None
    tokens: dict[str, PlacedTokenState] = Field(default_factory=dict)
    status: str = "imported"
