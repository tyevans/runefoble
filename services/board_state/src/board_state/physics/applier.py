"""State applier orchestrating physics simulations, grid snapping, and domain events."""

from __future__ import annotations

import math
from typing import Any
from uuid import uuid4

from board_state.models.physics import KnockbackResponse, SimulateThrowResponse
from board_state.physics.bounds import HeightfieldTerrain
from board_state.physics.simulator import simulate_dice_trajectory, simulate_knockback_trajectory
from runefoble_events.events import DiceSettled, PhysicsCollisionOccurred, TokenMoved


def _resolve_snap_cell(
    tok: Any, res: dict[str, Any], terrain: HeightfieldTerrain, max_c: int, max_r: int
) -> tuple[int, int]:
    sx, sy = (
        max(0, min(max_c - 1, int(round(res["final_x"])))),
        max(0, min(max_r - 1, int(round(res["final_y"])))),
    )
    if res["collided"] and res["collision_type"] == "wall":
        is_cliff = terrain.elevation_at(sx, sy) - terrain.elevation_at(tok.x, tok.y) > 0.5
        if (sx, sy) in terrain.wall_cells or is_cliff:
            sx, sy = tok.x, tok.y
            for pt in reversed(res["trajectory"]):
                cx, cy = int(math.floor(pt["x"])), int(math.floor(pt["y"]))
                if (cx, cy) not in terrain.wall_cells and (
                    terrain.elevation_at(cx, cy) - terrain.elevation_at(tok.x, tok.y) <= 0.5
                ):
                    return cx, cy
    return sx, sy


def _emit_collision(
    board: Any, tid: str, res: dict[str, Any], snap_pos: list[int], dx: float, dy: float
) -> None:
    c = res["collision_point"] or [snap_pos[0], snap_pos[1], 0.0]
    board.create_event(
        PhysicsCollisionOccurred,
        session_id=str(board.state.session_id),
        board_id=str(board.aggregate_id),
        entity_id=tid,
        entity_type="token",
        collision_type=res["collision_type"] or "wall",
        x=float(c[0]),
        y=float(c[1]),
        z=float(c[2]) if len(c) > 2 else 0.0,
        impact_velocity=res["impact_velocity"],
        impact_energy=res["impact_energy"],
        normal_x=-dx,
        normal_y=-dy,
        details={"distance_traveled_ft": res["distance_traveled_ft"]},
    )


def apply_token_knockback(
    board: Any,
    token_id: str,
    direction_x: float,
    direction_y: float,
    distance_ft: float = 10.0,
    mass: float = 1.0,
) -> KnockbackResponse:
    """Simulate knockback slide, halt upon collision with high walls, and snap to grid cell."""
    tid = str(token_id)
    if tid not in board.state.tokens:
        raise ValueError(f"Token '{token_id}' not found on grid")
    tok = board.state.tokens[tid]
    terrain = HeightfieldTerrain.from_board_state(board.state)
    res = simulate_knockback_trajectory(
        tok.x, tok.y, direction_x, direction_y, distance_ft, terrain, mass, token_id=tid
    )
    snap_x, snap_y = _resolve_snap_cell(tok, res, terrain, board.state.cols, board.state.rows)

    if res["collided"]:
        _emit_collision(board, tid, res, [snap_x, snap_y], direction_x, direction_y)

    if snap_x != tok.x or snap_y != tok.y:
        board.create_event(
            TokenMoved,
            session_id=board.aggregate_id,
            token_id=tid,
            name=tok.name,
            from_x=tok.x,
            from_y=tok.y,
            to_x=snap_x,
            to_y=snap_y,
            initiated_by="the_watcher",
        )
        if tok.is_friendly and board.state.fog_of_war_enabled:
            board._sync_revealed_fog(tid, snap_x, snap_y, tok.vision_radius)

    return KnockbackResponse(
        token_id=tid,
        from_x=tok.x,
        from_y=tok.y,
        to_x=snap_x,
        to_y=snap_y,
        settled_position=[snap_x, snap_y],
        distance_traveled_ft=res["distance_traveled_ft"],
        collided=res["collided"],
        collision_type=res["collision_type"],
        collision_point=res["collision_point"],
        impact_energy=res["impact_energy"],
        trajectory=res["trajectory"],
        elevation=float(terrain.elevation_at(snap_x, snap_y)),
        status="settled",
    )


def apply_dice_throw(
    board: Any,
    dice_type: str = "d20",
    origin: tuple[float, float, float] = (0.0, 0.0, 2.0),
    velocity: tuple[float, float, float] = (5.0, 5.0, 2.0),
    seed: int | None = None,
    dice_id: str | None = None,
    restitution: float = 0.5,
    friction: float = 0.3,
    target_face_value: int | None = None,
) -> SimulateThrowResponse:
    """Simulate tumbling 3D dice roll across board terrain, record collisions, and settle value."""
    terrain = HeightfieldTerrain.from_board_state(board.state)
    d_id = dice_id or f"dice-{uuid4()}"
    traj, (sx, sy, sz), bounces, face_val, cols = simulate_dice_trajectory(
        origin,
        velocity,
        dice_type,
        terrain,
        restitution,
        friction,
        seed=seed,
        target_face_value=target_face_value,
    )
    settled_cell = [
        max(0, min(board.state.cols - 1, int(math.floor(sx)))),
        max(0, min(board.state.rows - 1, int(math.floor(sy)))),
    ]
    board.create_event(
        DiceSettled,
        session_id=str(board.state.session_id),
        board_id=str(board.aggregate_id),
        dice_id=d_id,
        dice_type=dice_type,
        face_value=face_val,
        settled_x=sx,
        settled_y=sy,
        settled_z=sz,
        bounces=bounces,
        trajectory=traj,
    )
    return SimulateThrowResponse(
        dice_id=d_id,
        dice_type=dice_type,
        face_value=face_val,
        settled_x=sx,
        settled_y=sy,
        settled_z=sz,
        settled_cell=settled_cell,
        bounces=bounces,
        trajectory=traj,
        collisions=cols,
        status="settled",
    )
