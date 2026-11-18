"""Kinematic route measuring and ghost preview logic for board_state."""

from __future__ import annotations

from typing import Any, Literal

from board_state.rules.grid import validate_point_within_bounds
from board_state.rules.hazards import walk_path
from board_state.rules.movement import calculate_movement_path
from pydantic import BaseModel, Field


class WaypointInfo(BaseModel):
    x: int
    y: int
    step: int
    distance_ft: int
    is_difficult: bool = False
    hazard: str | None = None


class PreviewMoveRequest(BaseModel):
    token_id: str | None = None
    to_x: int
    to_y: int
    from_x: int | None = None
    from_y: int | None = None
    movement_budget: int | None = None


class PreviewMoveResponse(BaseModel):
    token_id: str
    token_name: str = ""
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    total_distance_ft: int
    base_distance_ft: int
    terrain_penalty_ft: int
    movement_cost: int
    budget_exceeded: bool = False
    waypoints: list[WaypointInfo] = Field(default_factory=list)
    difficult_cells: list[list[int]] = Field(default_factory=list)
    hazard_cells: list[list[int]] = Field(default_factory=list)
    hazard_triggered: str | None = None
    damage_dice: str | None = None


class GhostPreviewEvent(BaseModel):
    type: Literal["ghost_preview"] = "ghost_preview"
    status: Literal["staged", "confirmed", "cancelled"] = "staged"
    session_id: str
    preview: PreviewMoveResponse
    speaker_name: str | None = None
    raw_transcript: str | None = None
    timeout_seconds: int = 15


def compute_kinematic_route_preview(
    board_aggregate: Any,
    token_id: str,
    to_x: int,
    to_y: int,
    from_x: int | None = None,
    from_y: int | None = None,
    movement_budget: int | None = None,
) -> PreviewMoveResponse:
    """Calculate trajectory waypoints, 5-ft distance measurements, terrain penalties, and hazards.

    The cost and hazard results come from the same walk that the move applies, so the
    preview and the move report the same hazard dice.
    """
    state = board_aggregate.state
    token = state.tokens.get(token_id)
    token_name = token.name if token else token_id

    start_x = from_x if from_x is not None else (token.x if token else 0)
    start_y = from_y if from_y is not None else (token.y if token else 0)

    validate_point_within_bounds(to_x, to_y, state.cols, state.rows, "Target")

    path = calculate_movement_path(start_x, start_y, to_x, to_y)
    walk = walk_path(path, board_aggregate.get_terrain)

    waypoints: list[WaypointInfo] = []
    difficult_cells: list[list[int]] = []
    hazard_cells: list[list[int]] = []
    cumulative_distance_ft = 0
    terrain_penalty_ft = 0

    for idx, step in enumerate(walk.steps, start=1):
        # Normal = 5ft (cost 1). Difficult = +5ft penalty (total 10ft, cost 2)
        cumulative_distance_ft += 10 if step.is_difficult else 5

        if step.is_difficult:
            difficult_cells.append([step.x, step.y])
            terrain_penalty_ft += 5

        if step.hazard:
            hazard_cells.append([step.x, step.y])

        waypoints.append(
            WaypointInfo(
                x=step.x,
                y=step.y,
                step=idx,
                distance_ft=cumulative_distance_ft,
                is_difficult=step.is_difficult,
                hazard=step.hazard,
            )
        )

    hazard_triggered, damage_dice = walk.last_hazard or (None, None)
    total_cost = walk.cost
    budget_exceeded = movement_budget is not None and total_cost > movement_budget

    return PreviewMoveResponse(
        token_id=token_id,
        token_name=token_name,
        from_x=start_x,
        from_y=start_y,
        to_x=to_x,
        to_y=to_y,
        total_distance_ft=cumulative_distance_ft,
        base_distance_ft=len(path) * 5,
        terrain_penalty_ft=terrain_penalty_ft,
        movement_cost=total_cost,
        budget_exceeded=budget_exceeded,
        waypoints=waypoints,
        difficult_cells=difficult_cells,
        hazard_cells=hazard_cells,
        hazard_triggered=hazard_triggered,
        damage_dice=damage_dice,
    )
