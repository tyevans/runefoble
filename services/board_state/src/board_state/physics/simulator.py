"""Ballistic trajectories, impulse restitution bounces, and friction simulation."""

from __future__ import annotations

import math
import random
from typing import Any

from board_state.physics.bounds import HeightfieldTerrain


def _parse_dice_sides(dice_type: str) -> int:
    dt = dice_type.lower().strip()
    return max(2, int(dt[1:])) if dt.startswith("d") and dt[1:].isdigit() else 20


def _pt(x: float, y: float, z: float, t: float) -> dict[str, float]:
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "t": round(t, 3)}


def _col_dict(
    col_type: str, x: float, y: float, z: float, energy: float, **extra: Any
) -> dict[str, Any]:
    return {
        "type": col_type,
        "x": round(x, 3),
        "y": round(y, 3),
        "z": round(z, 3),
        "energy": round(energy, 2),
        **extra,
    }


def simulate_dice_trajectory(
    origin: tuple[float, float, float],
    velocity: tuple[float, float, float],
    dice_type: str,
    terrain: HeightfieldTerrain,
    restitution: float = 0.5,
    friction: float = 0.3,
    dt: float = 0.04,
    max_steps: int = 120,
    seed: int | None = None,
    target_face_value: int | None = None,
) -> tuple[list[dict[str, float]], tuple[float, float, float], int, int, list[dict[str, Any]]]:
    """Compute tumbling 3D ballistic trajectory, restitution bounces, and stopping coordinates."""
    g, drag = 9.81, 0.02
    x, y, z = origin
    vx, vy, vz = velocity
    bounces, trajectory, collisions = 0, [], []

    for step in range(max_steps):
        trajectory.append(_pt(x, y, z, step * dt))
        vz -= g * dt
        vx -= vx * drag * dt
        vy -= vy * drag * dt
        nx, ny, nz = x + vx * dt, y + vy * dt, z + vz * dt

        if nx <= 0.05 or nx >= terrain.cols - 0.05:
            vx, nx = -vx * restitution, max(0.05, min(float(terrain.cols) - 0.05, nx))
            bounces += 1
            collisions.append(_col_dict("boundary", nx, ny, nz, 0.5 * (vx**2 + vy**2)))
        if ny <= 0.05 or ny >= terrain.rows - 0.05:
            vy, ny = -vy * restitution, max(0.05, min(float(terrain.rows) - 0.05, ny))
            bounces += 1
            collisions.append(_col_dict("boundary", nx, ny, nz, 0.5 * (vx**2 + vy**2)))

        ground_z = terrain.elevation_at(nx, ny)
        if nz <= ground_z:
            nz = ground_z
            if abs(vz) > 0.2:
                vz, vx, vy = -vz * restitution, vx * (1.0 - friction), vy * (1.0 - friction)
                bounces += 1
                collisions.append(_col_dict("floor", nx, ny, nz, 0.5 * (vz**2)))
            else:
                vz, vx, vy = 0.0, vx * (1.0 - friction * 1.5), vy * (1.0 - friction * 1.5)

        hit_tok = terrain.check_token_collision(nx, ny, nz)
        if hit_tok:
            vx, vy = -vx * restitution, -vy * restitution
            bounces += 1
            collisions.append(
                _col_dict("token", nx, ny, nz, 0.5 * (vx**2 + vy**2), token_id=hit_tok)
            )

        x, y, z = nx, ny, nz
        if z <= ground_z + 0.05 and math.hypot(vx, vy, vz) < 0.15:
            break

    sides = _parse_dice_sides(dice_type)
    rng = random.Random(seed) if seed is not None else random.Random()
    settled_face = (
        max(1, min(sides, int(target_face_value)))
        if target_face_value is not None
        else rng.randint(1, sides)
    )
    return (
        trajectory,
        (round(x, 3), round(y, 3), round(z, 3)),
        bounces,
        settled_face,
        collisions,
    )


def simulate_knockback_trajectory(
    start_x: float,
    start_y: float,
    dir_x: float,
    dir_y: float,
    distance_ft: float,
    terrain: HeightfieldTerrain,
    mass: float = 1.0,
    max_step: float = 0.5,
    token_id: str = "",
) -> dict[str, Any]:
    """Calculate token knockback slide with terrain step collisions, friction, and impact energy."""
    mag = math.hypot(dir_x, dir_y) or 1.0
    dx, dy = dir_x / mag, dir_y / mag
    dist_cells, step_size = max(0.0, distance_ft) / 5.0, 0.1
    total_steps = max(1, int(round(dist_cells / step_size)))
    initial_v = max(1.0, distance_ft * 0.75)

    cur_x, cur_y, cur_z = start_x, start_y, terrain.elevation_at(start_x, start_y)
    trajectory: list[dict[str, float]] = []
    collided, col_type, col_pt = False, None, None
    impact_energy, impact_vel, distance_traveled = 0.0, 0.0, 0.0

    for step in range(total_steps):
        nx, ny = cur_x + dx * step_size, cur_y + dy * step_size
        nz = terrain.elevation_at(nx, ny)
        v_cur = max(0.5, initial_v * (1.0 - (step / total_steps)))

        if terrain.is_out_of_bounds(nx, ny):
            collided, col_type, col_pt = (
                True,
                "boundary",
                [round(cur_x, 3), round(cur_y, 3), round(cur_z, 3)],
            )
            impact_vel, impact_energy = v_cur, round(0.5 * mass * (v_cur**2), 2)
            break
        if terrain.is_wall_or_cliff(cur_x, cur_y, nx, ny, max_step=max_step):
            collided, col_type, col_pt = True, "wall", [round(nx, 3), round(ny, 3), round(nz, 3)]
            impact_vel, impact_energy = v_cur, round(0.5 * mass * (v_cur**2), 2)
            break
        hit_tok = terrain.check_token_collision(nx, ny, nz, ignore_token_id=token_id)
        if hit_tok:
            collided, col_type, col_pt = True, "token", [round(nx, 3), round(ny, 3), round(nz, 3)]
            impact_vel, impact_energy = v_cur, round(0.5 * mass * (v_cur**2), 2)
            break

        cur_x, cur_y, cur_z = nx, ny, nz
        distance_traveled += step_size * 5.0
        trajectory.append(_pt(cur_x, cur_y, cur_z, step * 0.02))

    return {
        "trajectory": trajectory,
        "final_x": cur_x,
        "final_y": cur_y,
        "final_z": cur_z,
        "distance_traveled_ft": round(distance_traveled, 1),
        "collided": collided,
        "collision_type": col_type,
        "collision_point": col_pt,
        "impact_velocity": round(impact_vel, 2),
        "impact_energy": impact_energy,
    }
