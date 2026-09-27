"""Terrain cell state and grid configuration schemas."""

from __future__ import annotations

from typing import Any

from board_state.models.tokens import PlacedTokenState
from pydantic import BaseModel


class TerrainCellState(BaseModel):
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None
    hazard_status: str | None = None


class TerrainDict(dict):
    """Dictionary supporting both 'x,y' string keys and (x, y) tuple keys."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, tuple):
            return super().__getitem__(f"{key[0]},{key[1]}")
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        if isinstance(key, tuple):
            super().__setitem__(f"{key[0]},{key[1]}", value)
        else:
            super().__setitem__(key, value)

    def __contains__(self, key: Any) -> bool:
        if isinstance(key, tuple):
            return super().__contains__(f"{key[0]},{key[1]}")
        return super().__contains__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, tuple):
            return super().get(f"{key[0]},{key[1]}", default)
        return super().get(key, default)


class ConfigureTerrainRequest(BaseModel):
    x: int
    y: int
    elevation: int = 0
    terrain_type: str = "normal"
    hazard: str | None = None


class VisibilityResponse(BaseModel):
    session_id: str
    cols: int
    rows: int
    fog_of_war_enabled: bool
    revealed_cells: list[list[int]]
    currently_visible_cells: list[list[int]]
    tokens: list[PlacedTokenState]
