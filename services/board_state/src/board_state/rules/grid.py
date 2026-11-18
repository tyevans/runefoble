"""Grid bounds, Chebyshev reach, party visibility and wall-to-obstacle extraction."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def is_within_bounds(x: int, y: int, cols: int, rows: int) -> bool:
    """Return True if coordinates (x, y) fall within grid boundaries."""
    return 0 <= x < cols and 0 <= y < rows


def validate_point_within_bounds(
    x: int, y: int, cols: int, rows: int, label: str = "Coordinates"
) -> None:
    """Raise ValueError if coordinates (x, y) are out of bounds."""
    if not is_within_bounds(x, y, cols, rows):
        raise ValueError(f"{label} ({x}, {y}) out of grid bounds")


def validate_cells_within_bounds(
    cells: list[list[int]], cols: int, rows: int, label: str = "Cell"
) -> None:
    """Raise ValueError if any coordinate in cells is out of bounds."""
    for c in cells:
        if len(c) < 2 or not is_within_bounds(c[0], c[1], cols, rows):
            raise ValueError(f"{label} coordinates {c} out of grid bounds")


def find_uncharted_cells(
    existing_cells: list[list[int]], candidate_cells: list[list[int]]
) -> list[list[int]]:
    """Return list of candidate cells not already present in existing cells."""
    existing = {tuple(c) for c in existing_cells}
    return [c for c in candidate_cells if tuple(c) not in existing]


def calculate_chebyshev_cells(
    cx: int, cy: int, radius: int, cols: int, rows: int
) -> list[list[int]]:
    """Calculate all bounded grid coordinates within Chebyshev distance radius."""
    cells: list[list[int]] = []
    min_x = max(0, cx - radius)
    max_x = min(cols - 1, cx + radius)
    min_y = max(0, cy - radius)
    max_y = min(rows - 1, cy + radius)

    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            cells.append([x, y])
    return cells


def compute_party_visibility(tokens: Iterable[Any], cols: int, rows: int) -> list[list[int]]:
    """Compute the union of all cells visible by friendly tokens."""
    seen: set[tuple[int, int]] = set()
    for token in tokens:
        if getattr(token, "is_friendly", False):
            for c in calculate_chebyshev_cells(token.x, token.y, token.vision_radius, cols, rows):
                seen.add((c[0], c[1]))
    return [list(c) for c in sorted(seen)]


def extract_wall_obstacles(
    wall_segments: list[dict[str, Any]], cols: int, rows: int
) -> list[tuple[int, int]]:
    """Extract unique in-bounds grid intersections from wall segments."""
    obstacle_coords: set[tuple[int, int]] = set()
    for seg in wall_segments:
        for pt in [("x1", "y1"), ("x2", "y2")]:
            px = int(round(seg.get(pt[0], 0)))
            py = int(round(seg.get(pt[1], 0)))
            if 0 <= px < cols and 0 <= py < rows:
                obstacle_coords.add((px, py))
    return sorted(obstacle_coords)
