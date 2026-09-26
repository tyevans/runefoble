"""Kinematic route measuring and ghost preview logic for board_state."""

from __future__ import annotations

import contextlib
from typing import Any, Literal

from fastapi import WebSocket
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


class BoardWebSocketManager:
    """Manages active live WebSocket connections per board / session."""

    def __init__(self) -> None:
        self.active_rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self.active_rooms:
            self.active_rooms[session_id] = []
        self.active_rooms[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self.active_rooms:
            with contextlib.suppress(ValueError):
                self.active_rooms[session_id].remove(websocket)
            if not self.active_rooms[session_id]:
                del self.active_rooms[session_id]

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        if session_id not in self.active_rooms:
            return
        dead_connections: list[WebSocket] = []
        for connection in self.active_rooms[session_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect(session_id, dead)


board_ws_manager = BoardWebSocketManager()


def compute_kinematic_route_preview(
    board_aggregate: Any,
    token_id: str,
    to_x: int,
    to_y: int,
    from_x: int | None = None,
    from_y: int | None = None,
    movement_budget: int | None = None,
) -> PreviewMoveResponse:
    """Calculate trajectory waypoints, 5-ft distance measurements, terrain penalties, and hazards."""
    state = board_aggregate.state
    token = state.tokens.get(token_id)
    token_name = token.name if token else token_id

    start_x = from_x if from_x is not None else (token.x if token else 0)
    start_y = from_y if from_y is not None else (token.y if token else 0)

    # Check bounds
    if not (0 <= to_x < state.cols and 0 <= to_y < state.rows):
        raise ValueError(f"Target coordinates ({to_x}, {to_y}) out of grid bounds")

    path = board_aggregate.calculate_movement_path(start_x, start_y, to_x, to_y)

    waypoints: list[WaypointInfo] = []
    difficult_cells: list[list[int]] = []
    hazard_cells: list[list[int]] = []
    cumulative_distance_ft = 0
    total_cost = 0
    base_distance_ft = len(path) * 5
    terrain_penalty_ft = 0

    hazard_triggered: str | None = None
    damage_dice: str | None = None

    for idx, (cx, cy) in enumerate(path, start=1):
        cell_terrain = board_aggregate.get_terrain(cx, cy)
        is_difficult = cell_terrain.terrain_type == "difficult"
        cell_hazard = cell_terrain.hazard

        # Normal = 5ft (cost 1). Difficult = +5ft penalty (total 10ft, cost 2)
        step_ft = 10 if is_difficult else 5
        cumulative_distance_ft += step_ft
        total_cost += 2 if is_difficult else 1

        if is_difficult:
            difficult_cells.append([cx, cy])
            terrain_penalty_ft += 5

        if cell_hazard:
            hazard_cells.append([cx, cy])
            if idx == len(path):  # Landing on hazard
                hazard_triggered = cell_hazard
                damage_dice = "2d10" if cell_hazard == "lava" else "1d6"

        waypoints.append(
            WaypointInfo(
                x=cx,
                y=cy,
                step=idx,
                distance_ft=cumulative_distance_ft,
                is_difficult=is_difficult,
                hazard=cell_hazard,
            )
        )

    budget_exceeded = movement_budget is not None and total_cost > movement_budget

    return PreviewMoveResponse(
        token_id=token_id,
        token_name=token_name,
        from_x=start_x,
        from_y=start_y,
        to_x=to_x,
        to_y=to_y,
        total_distance_ft=cumulative_distance_ft,
        base_distance_ft=base_distance_ft,
        terrain_penalty_ft=terrain_penalty_ft,
        movement_cost=total_cost,
        budget_exceeded=budget_exceeded,
        waypoints=waypoints,
        difficult_cells=difficult_cells,
        hazard_cells=hazard_cells,
        hazard_triggered=hazard_triggered,
        damage_dice=damage_dice,
    )
