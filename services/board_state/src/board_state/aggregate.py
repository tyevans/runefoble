"""Event-sourced BoardState aggregate using eventsource-py and modular handlers."""

from __future__ import annotations

from typing import Any

from board_state.handlers import (
    FogHandlerMixin,
    PhysicsHandlerMixin,
    TokensHandlerMixin,
    VFXHandlerMixin,
)
from board_state.models import BoardState, PlacedTokenState, TerrainCellState, TerrainDict
from board_state.rules import (
    DEFAULT_HAZARD_DAMAGE,
    extract_wall_obstacles,
    get_hazard_damage_dice,
    validate_point_within_bounds,
)
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.events import (
    BoardGridInitialized,
    TerrainCellModified,
    UniversalVTTImported,
)

__all__ = [
    "DEFAULT_HAZARD_DAMAGE",
    "BoardAggregate",
    "BoardState",
    "FogHandlerMixin",
    "PhysicsHandlerMixin",
    "PlacedTokenState",
    "TerrainCellState",
    "TerrainDict",
    "TokensHandlerMixin",
    "VFXHandlerMixin",
    "get_hazard_damage_dice",
]


class BoardAggregate(
    TokensHandlerMixin,
    FogHandlerMixin,
    VFXHandlerMixin,
    PhysicsHandlerMixin,
    DeclarativeAggregate[BoardState],
):
    """Event-sourced aggregate managing tactical combat grid, spatial tokens, and fog-of-war."""

    aggregate_type = "BoardState"
    requires_creation_event = True

    def initialize_grid(self, cols: int = 12, rows: int = 12, session_id: str = "") -> None:
        """Initialize new tactical grid dimensions."""
        self.create_event(
            BoardGridInitialized,
            session_id=self.aggregate_id,
            width=cols,
            height=rows,
            session_id_str=session_id,
        )

    def configure_terrain(
        self,
        x: int,
        y: int,
        elevation: int = 0,
        terrain_type: str = "normal",
        hazard: str | None = None,
    ) -> None:
        """Configure terrain properties of a cell on the board."""
        validate_point_within_bounds(x, y, self.state.cols, self.state.rows, "Terrain")
        self.create_event(
            TerrainCellModified,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            x=x,
            y=y,
            elevation=elevation,
            terrain_type=terrain_type,
            hazard=hazard,
        )

    def get_terrain(self, x: int, y: int) -> TerrainCellState:
        """Get terrain metadata for cell (x, y), defaulting to normal elevation 0."""
        cell = self.state.terrain_cells.get((x, y))
        return cell if cell is not None else TerrainCellState(x=x, y=y)

    def import_uvtt_map(
        self,
        cols: int,
        rows: int,
        pixels_per_grid: int = 70,
        background_asset_id: str | None = None,
        background_image_url: str | None = None,
        wall_segments: list[dict[str, Any]] | None = None,
        portals: list[dict[str, Any]] | None = None,
        lights: list[dict[str, Any]] | None = None,
    ) -> None:
        """Import Universal VTT map geometry, background imagery, and wall obstacles."""
        walls = wall_segments or []
        self.create_event(
            UniversalVTTImported,
            session_id=str(self.state.session_id),
            aggregate_id=self.aggregate_id,
            cols=cols,
            rows=rows,
            pixels_per_grid=pixels_per_grid,
            background_asset_id=background_asset_id,
            background_image_url=background_image_url,
            wall_segments=walls,
            portals=portals or [],
            lights=lights or [],
        )

        for idx, (ox, oy) in enumerate(extract_wall_obstacles(walls, cols, rows)):
            tid = f"wall-obs-{idx + 1}"
            if tid not in self.state.tokens:
                self.place_token(tid, f"Wall Obstacle {idx + 1}", "obstacle", ox, oy)

    @handles(BoardGridInitialized)
    def _on_grid_initialized(self, event: BoardGridInitialized) -> None:
        self._state = BoardState.initial(
            event.aggregate_id,
            event.session_id_str or str(event.aggregate_id),
            event.width,
            event.height,
        )

    @handles(UniversalVTTImported)
    def _on_map_imported(self, event: UniversalVTTImported) -> None:
        self._state = self.state.with_map_imported(
            cols=event.cols,
            rows=event.rows,
            pixels_per_grid=event.pixels_per_grid,
            background_asset_id=event.background_asset_id,
            background_image_url=event.background_image_url,
            wall_segments=event.wall_segments,
            portals=event.portals,
            lights=event.lights,
        )

    @handles(TerrainCellModified)
    def _on_terrain_modified(self, event: TerrainCellModified) -> None:
        self._state = self.state.with_terrain_modified_from_event(event)
