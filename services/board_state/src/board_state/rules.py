"""Static game balance rules, hazard damages, and spatial calculations for tactical boards."""

from collections.abc import Callable, Iterable
from typing import Any

DEFAULT_HAZARD_DAMAGE: dict[str, str] = {
    "lava": "2d10",
    "fire": "1d6",
    "acid": "2d6",
    "spikes": "2d4",
    "poison": "1d4",
}


def get_hazard_damage_dice(hazard_type: str | None, default: str = "1d6") -> str:
    """Return damage dice formula for a hazard type, defaulting to 1d6."""
    if not hazard_type:
        return default
    return DEFAULT_HAZARD_DAMAGE.get(hazard_type.lower(), default)


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


def calculate_movement_cost(
    path: list[tuple[int, int]], get_terrain_fn: Callable[[int, int], Any]
) -> int:
    """Calculate movement budget cost across path (difficult terrain costs 2x per cell)."""
    cost = 0
    for cx, cy in path:
        terrain = get_terrain_fn(cx, cy)
        if getattr(terrain, "terrain_type", "normal") == "difficult":
            cost += 2
        else:
            cost += 1
    return cost


def detect_path_hazards(
    path: list[tuple[int, int]], get_terrain_fn: Callable[[int, int], Any]
) -> list[tuple[str, str]]:
    """Inspect movement path and return list of (hazard_type, damage_dice) triggered."""
    hazards: list[tuple[str, str]] = []
    for cx, cy in path:
        terrain = get_terrain_fn(cx, cy)
        if terrain and terrain.hazard:
            hazards.append((terrain.hazard, get_hazard_damage_dice(terrain.hazard)))
    return hazards


# Convenient aliases for internal modules
calc_chebyshev = calculate_chebyshev_cells
calc_move_cost = calculate_movement_cost
calc_move_path = calculate_movement_path
calc_party_vis = compute_party_visibility
