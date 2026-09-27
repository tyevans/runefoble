"""Rotatable geometric Area of Effect (AoE) calculations and target intersection engine.

Supports standard TTRPG cones (53.13 degree spread), spheres, and lines,
with 15-degree angular snapping and square/hex grid containment testing.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from board_state.models import AoETemplateResponse, PlacedTokenState

SPREAD_CONE_DEG = 53.13  # Standard 5e cone spread angle (width = length)


def snap_angle(angle_deg: float, increment: float = 15.0) -> float:
    """Snap an angle in degrees to the nearest increment (default 15 degrees)."""
    if increment <= 0:
        return angle_deg % 360.0
    snapped = round(angle_deg / increment) * increment
    return snapped % 360.0


def _normalize_angle_diff(angle1: float, angle2: float) -> float:
    """Compute the absolute smallest angular difference between two angles in degrees."""
    diff = abs((angle1 - angle2 + 180.0) % 360.0 - 180.0)
    return diff


def get_grid_point_real_coords(
    grid_x: float, grid_y: float, grid_type: str = "square"
) -> tuple[float, float]:
    """Convert grid coordinate to feet space (5ft per square cell center)."""
    if grid_type == "hex":
        # Pointy-topped hex geometry: cell spacing in feet (5ft per hex diameter)
        # horizontal distance between columns = 5 * sqrt(3)/2, vertical = 5 * 0.75
        col_offset = 0.5 if int(grid_y) % 2 == 1 else 0.0
        real_x = (grid_x + 0.5 + col_offset) * (5.0 * math.sqrt(3) / 2.0)
        real_y = (grid_y + 0.5) * (5.0 * 0.75)
        return real_x, real_y
    # Standard square grid: 1 square = 5 ft, center of cell (x, y) is at (x + 0.5, y + 0.5) * 5
    return (grid_x + 0.5) * 5.0, (grid_y + 0.5) * 5.0


def is_point_in_aoe(
    target_real_x: float,
    target_real_y: float,
    shape: Literal["cone", "sphere", "line", "cube"] | str,
    origin_real_x: float,
    origin_real_y: float,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
) -> bool:
    """Test if a point in real coordinate space (feet) is enclosed by an AoE shape."""
    dx = target_real_x - origin_real_x
    dy = target_real_y - origin_real_y
    distance_ft = math.hypot(dx, dy)

    shape = shape.lower()

    if shape == "cone":
        cone_radius = radius_ft if radius_ft is not None else 15.0
        if distance_ft <= 1e-4:
            return True
        if distance_ft > cone_radius + 0.01:
            return False

        point_angle = math.degrees(math.atan2(dy, dx)) % 360.0
        angle_diff = _normalize_angle_diff(point_angle, direction_deg % 360.0)
        half_spread = SPREAD_CONE_DEG / 2.0  # 26.565 degrees
        return angle_diff <= (half_spread + 0.01)

    elif shape == "sphere":
        sphere_radius = radius_ft if radius_ft is not None else 20.0
        return distance_ft <= (sphere_radius + 0.01)

    elif shape == "line":
        line_length = length_ft if length_ft is not None else 30.0
        line_width = width_ft if width_ft is not None else 5.0

        rad = math.radians(direction_deg)
        ux = math.cos(rad)
        uy = math.sin(rad)
        # Normal vector perpendicular to direction
        vx = -math.sin(rad)
        vy = math.cos(rad)

        proj_along = dx * ux + dy * uy
        proj_perp = abs(dx * vx + dy * vy)

        return -0.01 <= proj_along <= (line_length + 0.01) and proj_perp <= (
            line_width / 2.0 + 0.01
        )

    elif shape == "cube":
        size = radius_ft if radius_ft is not None else (length_ft or 15.0)
        half_size = size / 2.0
        return abs(dx) <= half_size + 0.01 and abs(dy) <= half_size + 0.01

    return False


def is_token_in_aoe(
    token_x: int,
    token_y: int,
    shape: str,
    origin_x: float,
    origin_y: float,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
    grid_type: str = "square",
) -> bool:
    """Determine if a token at integer grid coordinates is within the AoE geometry."""
    tok_rx, tok_ry = get_grid_point_real_coords(token_x, token_y, grid_type=grid_type)
    # Origin is given in grid coordinates; convert to feet
    if grid_type == "hex":
        orig_rx, orig_ry = get_grid_point_real_coords(
            origin_x - 0.5, origin_y - 0.5, grid_type=grid_type
        )
    else:
        orig_rx, orig_ry = origin_x * 5.0, origin_y * 5.0

    return is_point_in_aoe(
        target_real_x=tok_rx,
        target_real_y=tok_ry,
        shape=shape,
        origin_real_x=orig_rx,
        origin_real_y=orig_ry,
        direction_deg=direction_deg,
        radius_ft=radius_ft,
        length_ft=length_ft,
        width_ft=width_ft,
    )


def compute_affected_cells(
    cols: int,
    rows: int,
    shape: str,
    origin_x: float,
    origin_y: float,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
    grid_type: str = "square",
) -> list[list[int]]:
    """Calculate all grid cell coordinates [x, y] covered by the AoE geometry."""
    affected: list[list[int]] = []
    if grid_type == "hex":
        orig_rx, orig_ry = get_grid_point_real_coords(
            origin_x - 0.5, origin_y - 0.5, grid_type=grid_type
        )
    else:
        orig_rx, orig_ry = origin_x * 5.0, origin_y * 5.0

    for cy in range(rows):
        for cx in range(cols):
            cell_rx, cell_ry = get_grid_point_real_coords(cx, cy, grid_type=grid_type)
            if is_point_in_aoe(
                target_real_x=cell_rx,
                target_real_y=cell_ry,
                shape=shape,
                origin_real_x=orig_rx,
                origin_real_y=orig_ry,
                direction_deg=direction_deg,
                radius_ft=radius_ft,
                length_ft=length_ft,
                width_ft=width_ft,
            ):
                affected.append([cx, cy])
    return affected


def evaluate_aoe_targets(
    tokens: dict[str, PlacedTokenState],
    cols: int,
    rows: int,
    shape: str,
    origin_x: float,
    origin_y: float,
    direction_deg: float = 0.0,
    radius_ft: float | None = None,
    length_ft: float | None = None,
    width_ft: float | None = 5.0,
    grid_type: str = "square",
    template_id: str = "",
    caster_token_id: str | None = None,
    spell_name: str | None = None,
) -> AoETemplateResponse:
    """Evaluate target tokens and affected grid cells enclosed by the AoE geometry."""
    from board_state.models import AoETemplateResponse

    snapped_direction = snap_angle(direction_deg)
    affected_tokens: list[PlacedTokenState] = []
    affected_token_ids: list[str] = []

    for tok in tokens.values():
        if is_token_in_aoe(
            token_x=tok.x,
            token_y=tok.y,
            shape=shape,
            origin_x=origin_x,
            origin_y=origin_y,
            direction_deg=snapped_direction,
            radius_ft=radius_ft,
            length_ft=length_ft,
            width_ft=width_ft,
            grid_type=grid_type,
        ):
            affected_tokens.append(tok)
            affected_token_ids.append(tok.token_id)

    affected_cells = compute_affected_cells(
        cols=cols,
        rows=rows,
        shape=shape,
        origin_x=origin_x,
        origin_y=origin_y,
        direction_deg=snapped_direction,
        radius_ft=radius_ft,
        length_ft=length_ft,
        width_ft=width_ft,
        grid_type=grid_type,
    )

    return AoETemplateResponse(
        template_id=template_id,
        caster_token_id=caster_token_id,
        shape=shape,
        origin_x=origin_x,
        origin_y=origin_y,
        direction_deg=snapped_direction,
        radius_ft=radius_ft,
        length_ft=length_ft,
        width_ft=width_ft,
        spell_name=spell_name,
        affected_token_ids=affected_token_ids,
        affected_tokens=affected_tokens,
        affected_cells=affected_cells,
    )
