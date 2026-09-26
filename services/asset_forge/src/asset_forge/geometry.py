"""Spatial geometry analysis and procedural room/wall layout generation."""

from __future__ import annotations

import hashlib
from typing import Any

from asset_forge.models import (
    BoardGeometryPayload,
    DoorSegment,
    HazardCell,
    WallSegment,
)


def infer_theme_from_prompt(prompt: str) -> tuple[str, str, str]:
    """Infer theme, primary hazard type, and damage dice from natural language prompt."""
    p = prompt.lower()

    if any(
        k in p
        for k in ["forge", "lava", "volcano", "volcanic", "magma", "fire", "dwarf", "dwarven"]
    ):
        return "dwarven_forge", "lava", "2d10"
    if any(
        k in p
        for k in ["crypt", "tomb", "graveyard", "necropolis", "undead", "catacomb", "skeleton"]
    ):
        return "crypt", "spikes", "1d8"
    if any(k in p for k in ["forest", "swamp", "marsh", "bog", "river", "water", "jungle"]):
        return "swamp", "deep_water", "1d4"
    if any(k in p for k in ["arcane", "void", "astral", "portal", "magic", "sanctuary"]):
        return "arcane_sanctuary", "arcane_void", "2d6"
    if any(k in p for k in ["cavern", "cave", "chasm", "mine", "crystal"]):
        return "cavern", "chasm", "1d10"

    return "dungeon", "acid", "1d6"


def generate_map_layout(
    prompt: str,
    width: int,
    height: int,
    wall_density: float = 0.2,
    hazard_density: float = 0.1,
    theme_override: str | None = None,
) -> tuple[str, list[WallSegment], list[HazardCell], list[DoorSegment], list[list[int]]]:
    """Generate structured tactical battlemap grid, walls, hazards, and doors from prompt."""
    theme, hazard_type, damage_dice = infer_theme_from_prompt(prompt)
    if theme_override:
        theme = theme_override

    # Deterministic pseudo-random seed based on prompt and dimensions
    seed_int = int(hashlib.sha256(f"{prompt}:{width}x{height}".encode()).hexdigest()[:8], 16)

    # 0 = open floor, 1 = wall obstacle, 2 = hazard
    grid: list[list[int]] = [[0 for _ in range(width)] for _ in range(height)]

    # 1. Outer perimeter walls
    for x in range(width):
        grid[0][x] = 1
        grid[height - 1][x] = 1
    for y in range(height):
        grid[y][0] = 1
        grid[y][width - 1] = 1

    # 2. Divide into rooms / pillars based on wall_density
    wall_segments: list[WallSegment] = []
    doors: list[DoorSegment] = []

    # Outer wall boundary segments
    wall_segments.append(WallSegment(x1=0, y1=0, x2=width, y2=0, wall_type="perimeter"))
    wall_segments.append(WallSegment(x1=width, y1=0, x2=width, y2=height, wall_type="perimeter"))
    wall_segments.append(WallSegment(x1=width, y1=height, x2=0, y2=height, wall_type="perimeter"))
    wall_segments.append(WallSegment(x1=0, y1=height, x2=0, y2=0, wall_type="perimeter"))

    # Add dividing internal walls with door openings
    mid_x = width // 2
    mid_y = height // 2

    # Vertical divider
    door_y = mid_y + (seed_int % 3) - 1
    for y in range(1, height - 1):
        if y == door_y or y == door_y + 1:
            doors.append(DoorSegment(x1=mid_x, y1=y, x2=mid_x + 1, y2=y, state="closed"))
        else:
            grid[y][mid_x] = 1
    wall_segments.append(WallSegment(x1=mid_x, y1=1, x2=mid_x, y2=door_y, is_door=False))
    wall_segments.append(
        WallSegment(x1=mid_x, y1=door_y + 2, x2=mid_x, y2=height - 1, is_door=False)
    )

    # Horizontal divider in left wing
    door_x = mid_x // 2
    for x in range(1, mid_x):
        if x != door_x:
            grid[mid_y][x] = 1
        else:
            doors.append(DoorSegment(x1=x, y1=mid_y, x2=x + 1, y2=mid_y, state="closed"))
    wall_segments.append(WallSegment(x1=1, y1=mid_y, x2=door_x, y2=mid_y, is_door=False))
    wall_segments.append(WallSegment(x1=door_x + 1, y1=mid_y, x2=mid_x, y2=mid_y, is_door=False))

    # Add themed pillars or obstacles
    step = max(3, int(1 / (wall_density + 0.05)))
    for y in range(2, height - 2, step):
        for x in range(mid_x + 2, width - 2, step):
            if (x * 7 + y * 13 + seed_int) % 10 < int(wall_density * 10):
                grid[y][x] = 1
                wall_segments.append(
                    WallSegment(x1=x, y1=y, x2=x + 1, y2=y + 1, wall_type="pillar")
                )

    # 3. Hazard placement (e.g. lava canal or acid pool)
    hazard_cells: list[HazardCell] = []
    hazard_target_count = max(2, int((width * height) * hazard_density * 0.15))

    # Canal or pool coordinates in right quadrant
    canal_x = mid_x + max(2, (width - mid_x) // 2)
    for y in range(2, min(height - 2, 2 + hazard_target_count)):
        if grid[y][canal_x] == 0:
            grid[y][canal_x] = 2
            hazard_cells.append(
                HazardCell(
                    x=canal_x,
                    y=y,
                    hazard_type=hazard_type,
                    damage_dice=damage_dice,
                    terrain_type="difficult",
                )
            )

    return theme, wall_segments, hazard_cells, doors, grid


def build_board_geometry_payload(
    wall_segments: list[WallSegment],
    hazard_cells: list[HazardCell],
    doors: list[DoorSegment],
) -> BoardGeometryPayload:
    """Format spatial layout into structured payloads ready for board_state service mutators."""
    terrain_mutations: list[dict[str, Any]] = [
        {
            "x": h.x,
            "y": h.y,
            "elevation": 0,
            "terrain_type": h.terrain_type,
            "hazard": h.hazard_type,
            "damage_dice": h.damage_dice,
        }
        for h in hazard_cells
    ]

    obstacle_tokens: list[dict[str, Any]] = [
        {
            "name": f"Obstacle Wall ({w.x1},{w.y1})",
            "token_type": "obstacle",
            "x": w.x1,
            "y": w.y1,
            "hp": None,
            "is_friendly": False,
        }
        for w in wall_segments
        if w.wall_type == "pillar"
    ]

    return BoardGeometryPayload(
        terrain_mutations=terrain_mutations,
        obstacle_tokens=obstacle_tokens,
        wall_segments=[w.model_dump() for w in wall_segments],
        doors=[d.model_dump() for d in doors],
    )
