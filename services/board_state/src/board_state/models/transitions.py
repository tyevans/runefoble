"""Board aggregate state transition and mutation helper mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from board_state.aoe_models import AoETemplateState
from board_state.models.terrain import TerrainCellState, TerrainDict
from board_state.models.tokens import PlacedTokenState
from board_state.models.vfx import BoardDecalState

if TYPE_CHECKING:
    from board_state.models.board import BoardState


class BoardTransitionsMixin:
    """Provides pure state mutation helpers for BoardState."""

    def with_map_imported(
        self: BoardState,
        cols: int,
        rows: int,
        pixels_per_grid: int = 70,
        background_asset_id: str | None = None,
        background_image_url: str | None = None,
        wall_segments: list[dict[str, Any]] | None = None,
        portals: list[dict[str, Any]] | None = None,
        lights: list[dict[str, Any]] | None = None,
    ) -> BoardState:
        return self.model_copy(
            update={
                "cols": cols,
                "rows": rows,
                "pixels_per_grid": pixels_per_grid,
                "background_asset_id": background_asset_id,
                "background_image_url": background_image_url,
                "wall_segments": wall_segments if wall_segments is not None else self.wall_segments,
                "portals": portals if portals is not None else self.portals,
                "lights": lights if lights is not None else self.lights,
            }
        )

    def with_terrain_modified_from_event(self: BoardState, event: Any) -> BoardState:
        return self.with_terrain_modified(
            x=event.x,
            y=event.y,
            elevation=event.elevation,
            terrain_type=event.terrain_type,
            hazard=event.hazard,
        )

    def with_terrain_modified(
        self: BoardState, x: int, y: int, elevation: int, terrain_type: str, hazard: str | None
    ) -> BoardState:
        cells = TerrainDict(self.terrain_cells)
        hazard_status = "active" if hazard else None
        cell_state = TerrainCellState(
            x=x,
            y=y,
            elevation=elevation,
            terrain_type=terrain_type,
            hazard=hazard,
            hazard_status=hazard_status,
        )
        cells[(x, y)] = cell_state
        active_hazards = sorted({c.hazard for c in cells.values() if c.hazard})
        return self.model_copy(update={"terrain_cells": cells, "active_hazards": active_hazards})

    def with_hazard_triggered(self: BoardState, token_id: str, hazard_type: str) -> BoardState:
        tokens = dict(self.tokens)
        tid = str(token_id)
        if tid in tokens:
            tokens[tid] = tokens[tid].model_copy(
                update={"active_hazard": hazard_type, "hazard_status": "active"}
            )
        return self.model_copy(update={"tokens": tokens})

    def with_token_placed(self: BoardState, token: PlacedTokenState) -> BoardState:
        tokens = dict(self.tokens)
        tokens[str(token.token_id)] = token
        return self.model_copy(update={"tokens": tokens})

    def with_token_moved(
        self: BoardState, token_id: str, to_x: int, to_y: int, active_hazard: str | None
    ) -> BoardState:
        tokens = dict(self.tokens)
        tid_str = str(token_id)
        if tid_str in tokens:
            h_status = "active" if active_hazard else None
            tokens[tid_str] = tokens[tid_str].model_copy(
                update={
                    "x": to_x,
                    "y": to_y,
                    "active_hazard": active_hazard,
                    "hazard_status": h_status,
                }
            )
        return self.model_copy(update={"tokens": tokens})

    def without_token(self: BoardState, token_id: str) -> BoardState:
        tokens = dict(self.tokens)
        tokens.pop(str(token_id), None)
        return self.model_copy(update={"tokens": tokens})

    def with_fog_revealed(self: BoardState, new_cells: list[list[int]]) -> BoardState:
        existing = {tuple(c) for c in self.revealed_cells}
        for cell in new_cells:
            existing.add(tuple(cell))
        ordered = [list(c) for c in sorted(existing)]
        return self.model_copy(update={"revealed_cells": ordered})

    def with_fog_shrouded(self: BoardState, shrouded_cells: list[list[int]]) -> BoardState:
        to_remove = {tuple(c) for c in shrouded_cells}
        remaining = [c for c in self.revealed_cells if tuple(c) not in to_remove]
        return self.model_copy(update={"revealed_cells": remaining})

    def with_token_action(self: BoardState, token_id: str, action: str) -> BoardState:
        tokens = dict(self.tokens)
        tid_str = str(token_id)
        if tid_str in tokens:
            tokens[tid_str] = tokens[tid_str].model_copy(update={"active_action": action})
        return self.model_copy(update={"tokens": tokens})

    def with_aoe_template_placed(self: BoardState, template: AoETemplateState) -> BoardState:
        templates = [t for t in self.active_aoe_templates if t.template_id != template.template_id]
        templates.append(template)
        return self.model_copy(update={"active_aoe_templates": templates})

    def without_aoe_template(self: BoardState, template_id: str) -> BoardState:
        templates = [t for t in self.active_aoe_templates if t.template_id != template_id]
        return self.model_copy(update={"active_aoe_templates": templates})

    def with_area_effect(
        self: BoardState,
        affected_cells: list[list[int]],
        decal_type: str | None = "scorched_earth",
        decal_duration_rounds: int = 2,
    ) -> BoardState:
        decals = list(self.active_decals)
        if decal_type:
            for cell in affected_cells:
                cx, cy = cell[0], cell[1]
                decals.append(
                    BoardDecalState(
                        decal_id=f"decal-{uuid4().hex[:8]}",
                        x=cx,
                        y=cy,
                        decal_type=decal_type,
                        duration_rounds=decal_duration_rounds,
                        rounds_remaining=decal_duration_rounds,
                        opacity=1.0,
                    )
                )
        return self.model_copy(update={"active_decals": decals})

    def with_decals_decayed(self: BoardState, rounds: int = 1) -> BoardState:
        updated = []
        for d in self.active_decals:
            rem = d.rounds_remaining - rounds
            if rem > 0:
                updated.append(
                    d.model_copy(
                        update={
                            "rounds_remaining": rem,
                            "opacity": max(0.2, rem / d.duration_rounds),
                        }
                    )
                )
        return self.model_copy(update={"active_decals": updated})
