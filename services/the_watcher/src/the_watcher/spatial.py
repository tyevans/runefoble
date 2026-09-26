"""Tactical spatial math and coordinate bounding for The Watcher."""

from __future__ import annotations


def compute_directional_deltas(direction: str, steps: int) -> tuple[int, int]:
    """Compute (dx, dy) coordinate changes from a cardinal or diagonal direction string."""
    direction_clean = direction.lower().replace("-", "")
    dx, dy = 0, 0
    if direction_clean in ("north", "up"):
        dy = -steps
    elif direction_clean in ("south", "down"):
        dy = steps
    elif direction_clean in ("east", "right"):
        dx = steps
    elif direction_clean in ("west", "left"):
        dx = -steps
    elif direction_clean == "northeast":
        dx = steps
        dy = -steps
    elif direction_clean == "northwest":
        dx = -steps
        dy = -steps
    elif direction_clean == "southeast":
        dx = steps
        dy = steps
    elif direction_clean == "southwest":
        dx = -steps
        dy = steps
    return dx, dy


def calculate_steps(raw_distance: int, unit: str | None) -> int:
    """Convert distance and optional unit into discrete tactical grid steps."""
    unit_lower = (unit or "").lower()
    if unit_lower in ("feet", "foot", "ft"):
        return max(1, raw_distance // 5) if raw_distance > 0 else 0
    return raw_distance


def calculate_bounded_destination(
    from_x: int,
    from_y: int,
    dx: int,
    dy: int,
    cols: int = 12,
    rows: int = 12,
) -> tuple[int, int]:
    """Calculate target coordinates clamped strictly within tactical grid bounds [0, cols-1] and [0, rows-1]."""
    to_x = max(0, min(cols - 1, from_x + dx))
    to_y = max(0, min(rows - 1, from_y + dy))
    return to_x, to_y
