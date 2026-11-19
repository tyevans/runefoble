"""Event-sourced BoardState aggregate using eventsource-py and modular handlers."""

from __future__ import annotations

from typing import Any

from board_state.camera.models import CameraTarget
from board_state.handlers import (
    DoorsLightsHandlerMixin,
    FogHandlerMixin,
    PhysicsHandlerMixin,
    TokensHandlerMixin,
    TrapsHandlerMixin,
    VFXHandlerMixin,
)
from board_state.models import BoardState, PlacedTokenState, TerrainCellState
from board_state.rules.grid import extract_wall_obstacles, validate_point_within_bounds
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.events import (
    BoardGridInitialized,
    CameraFocused,
    EncounterPlacementsApplied,
    ForgedBattlemapApplied,
    TerrainCellModified,
    UniversalVTTImported,
)

APPLIED_ENCOUNTER_LEDGER_SIZE = 1000

__all__ = [
    "BoardAggregate",
    "PlacedTokenState",
]


class BoardAggregate(
    TrapsHandlerMixin,
    DoorsLightsHandlerMixin,
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

    def focus_camera(self, target: CameraTarget) -> None:
        """Record the spectator camera target for this session."""
        self.create_event(
            CameraFocused,
            session_id=self.aggregate_id,
            target_x=target.target_x,
            target_y=target.target_y,
            zoom=target.zoom,
            duration_ms=target.duration_ms,
            easing=target.easing,
            reason=target.reason,
            active_token_id=target.active_token_id,
            active_character_id=target.active_character_id,
            focused_at=target.timestamp,
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
        doors: dict[str, Any] | None = None,
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
            doors=doors or {},
            lights=lights or [],
        )

        self._place_wall_obstacles(walls, cols, rows)

    def record_encounter_applied(self, source_event_id: str, token_ids: list[str]) -> None:
        """Record that one combat start's placements were applied (TASK-0749)."""
        self.create_event(
            EncounterPlacementsApplied,
            session_id=str(self.state.session_id),
            source_event_id=source_event_id,
            token_ids=token_ids,
        )

    def apply_forged_battlemap(
        self,
        asset_id: str,
        cols: int,
        rows: int,
        wall_segments: list[dict[str, Any]],
        hazard_cells: list[dict[str, Any]],
    ) -> None:
        """Make a forged battlemap the board geometry: grid size, walls, obstacles, and hazards.

        The grid event is recorded first, so the hazard bounds check uses the new grid size.
        """
        self.create_event(
            ForgedBattlemapApplied,
            session_id=str(self.state.session_id),
            aggregate_id=self.aggregate_id,
            asset_id=asset_id,
            cols=cols,
            rows=rows,
            wall_segments=wall_segments,
        )
        for cell in hazard_cells:
            self.configure_terrain(
                x=cell["x"],
                y=cell["y"],
                elevation=0,
                terrain_type=cell["terrain_type"],
                hazard=cell["hazard_type"],
            )
        self._place_wall_obstacles(wall_segments, cols, rows)

    def _place_wall_obstacles(self, walls: list[dict[str, Any]], cols: int, rows: int) -> None:
        """Place one obstacle token per wall obstacle cell. A token that exists is kept."""
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
            doors=getattr(event, "doors", {}),
        )

    @handles(ForgedBattlemapApplied)
    def _on_forged_battlemap_applied(self, event: ForgedBattlemapApplied) -> None:
        self._state = self.state.model_copy(
            update={
                "cols": event.cols,
                "rows": event.rows,
                "wall_segments": list(event.wall_segments),
                "forged_asset_id": event.asset_id,
            }
        )

    @handles(EncounterPlacementsApplied)
    def _on_encounter_placements_applied(self, event: EncounterPlacementsApplied) -> None:
        """Keep the last applied combat start ids, so a redelivery is a no-op (TASK-0749)."""
        ledger = [*self.state.applied_encounter_event_ids, event.source_event_id]
        self._state = self.state.model_copy(
            update={"applied_encounter_event_ids": ledger[-APPLIED_ENCOUNTER_LEDGER_SIZE:]}
        )

    @handles(CameraFocused)
    def _on_camera_focused(self, event: CameraFocused) -> None:
        self._state = self.state.model_copy(
            update={
                "camera": CameraTarget(
                    target_x=event.target_x,
                    target_y=event.target_y,
                    zoom=event.zoom,
                    duration_ms=event.duration_ms,
                    easing=event.easing,
                    active_token_id=event.active_token_id,
                    active_character_id=event.active_character_id,
                    reason=event.reason,
                    timestamp=event.focused_at,
                )
            }
        )

    @handles(TerrainCellModified)
    def _on_terrain_modified(self, event: TerrainCellModified) -> None:
        self._state = self.state.with_terrain_modified_from_event(event)
