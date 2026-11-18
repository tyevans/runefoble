"""Sphere, cone, line, and cube containment in feet. The single rule for AoE and spell blooms.

A cell is inside a shape when its centre is inside the shape. The origin is the
centre of its origin cell. Every caller (AoE evaluation, spell VFX bloom, token
targeting) uses this module.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Literal

from board_state.geometry.grid import cell_centre_ft

SPREAD_CONE_DEG = 53.13  # Standard 5e cone spread angle (width = length)
TOLERANCE_FT = 0.01

Shape = Literal["cone", "sphere", "line", "cube"]


def _normalize_angle_diff(angle1: float, angle2: float) -> float:
    """Return the absolute smallest angular difference between two angles in degrees."""
    return abs((angle1 - angle2 + 180.0) % 360.0 - 180.0)


def point_in_shape(
    point_x: float,
    point_y: float,
    shape: str,
    origin_x: float,
    origin_y: float,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
) -> bool:
    """Return True when a point in feet lies inside the AoE shape."""
    dx = point_x - origin_x
    dy = point_y - origin_y
    distance_ft = math.hypot(dx, dy)
    kind = shape.lower()

    if kind == "cone":
        cone_radius = radius_ft if radius_ft is not None else 15.0
        if distance_ft <= 1e-4:
            return True
        if distance_ft > cone_radius + TOLERANCE_FT:
            return False
        point_angle = math.degrees(math.atan2(dy, dx)) % 360.0
        angle_diff = _normalize_angle_diff(point_angle, direction_deg % 360.0)
        return angle_diff <= (SPREAD_CONE_DEG / 2.0 + TOLERANCE_FT)

    if kind == "sphere":
        sphere_radius = radius_ft if radius_ft is not None else 20.0
        return distance_ft <= (sphere_radius + TOLERANCE_FT)

    if kind == "line":
        line_length = length_ft if length_ft is not None else 30.0
        line_width = width_ft if width_ft is not None else 5.0
        rad = math.radians(direction_deg)
        proj_along = dx * math.cos(rad) + dy * math.sin(rad)
        proj_perp = abs(-dx * math.sin(rad) + dy * math.cos(rad))
        return -TOLERANCE_FT <= proj_along <= (line_length + TOLERANCE_FT) and proj_perp <= (
            line_width / 2.0 + TOLERANCE_FT
        )

    if kind == "cube":
        size = radius_ft if radius_ft is not None else (length_ft or 15.0)
        half_size = size / 2.0
        rad = math.radians(direction_deg)
        proj_x = abs(dx * math.cos(rad) + dy * math.sin(rad))
        proj_y = abs(-dx * math.sin(rad) + dy * math.cos(rad))
        return proj_x <= half_size + TOLERANCE_FT and proj_y <= half_size + TOLERANCE_FT

    return False


def cell_in_shape(
    col: int,
    row: int,
    shape: str,
    origin_col: int,
    origin_row: int,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
    grid_type: str = "square",
) -> bool:
    """Return True when the centre of cell (col, row) lies inside the shape placed on the origin cell."""
    cell_x, cell_y = cell_centre_ft(col, row, grid_type)
    origin_ft_x, origin_ft_y = cell_centre_ft(origin_col, origin_row, grid_type)
    return point_in_shape(
        cell_x,
        cell_y,
        shape,
        origin_ft_x,
        origin_ft_y,
        direction_deg=direction_deg,
        radius_ft=radius_ft,
        length_ft=length_ft,
        width_ft=width_ft,
    )


def cells_in_shape(
    cols: int,
    rows: int,
    shape: str,
    origin_col: int,
    origin_row: int,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
    grid_type: str = "square",
) -> list[list[int]]:
    """Return every in-bounds cell [col, row] whose centre lies inside the shape."""
    return [
        [col, row]
        for row in range(rows)
        for col in range(cols)
        if cell_in_shape(
            col,
            row,
            shape,
            origin_col,
            origin_row,
            direction_deg=direction_deg,
            radius_ft=radius_ft,
            length_ft=length_ft,
            width_ft=width_ft,
            grid_type=grid_type,
        )
    ]


def cells_as_set(cells: Iterable[list[int]]) -> set[tuple[int, int]]:
    """Return cells as a set of (col, row) tuples for membership tests."""
    return {(cell[0], cell[1]) for cell in cells}
