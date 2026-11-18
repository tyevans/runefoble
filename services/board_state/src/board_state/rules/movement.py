"""Straight-line movement path between two grid cells."""

from __future__ import annotations


def calculate_movement_path(
    from_x: int, from_y: int, to_x: int, to_y: int
) -> list[tuple[int, int]]:
    """Calculate line of cells traversed when moving between coordinates."""
    dx = to_x - from_x
    dy = to_y - from_y
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        return []
    path: list[tuple[int, int]] = []
    for step in range(1, steps + 1):
        cx = round(from_x + step * (dx / steps))
        cy = round(from_y + step * (dy / steps))
        path.append((int(cx), int(cy)))
    return path
