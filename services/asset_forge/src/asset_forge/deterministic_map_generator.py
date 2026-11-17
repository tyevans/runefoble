"""Deterministic battlemap layout: the default MapGenerator adapter.

This generator needs no model and no network. It uses keyword themes and a
seeded random generator. The prompt, the seed and the size all feed the
generator, so the same inputs always give the same layout and other inputs
give other layouts. It does not run diffusion or any learned model.
"""

from __future__ import annotations

import hashlib
import random
from typing import ClassVar

from asset_forge.map_generator import MapGenerator, MapLayout
from asset_forge.models import DoorSegment, HazardCell, WallSegment


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


def _effective_seed(prompt: str, seed: int | None, width: int, height: int) -> int:
    """Use the caller seed. Without one, derive a stable seed from the prompt and size."""
    if seed is not None:
        return seed
    return int(hashlib.sha256(f"{prompt}:{width}x{height}".encode()).hexdigest()[:8], 16)


def _layout_rng(prompt: str, seed: int | None, width: int, height: int) -> random.Random:
    """Random generator keyed by prompt, seed and size. Each input gives its own stream."""
    effective = _effective_seed(prompt, seed, width, height)
    material = f"{prompt}|{effective}|{width}x{height}".encode()
    return random.Random(hashlib.sha256(material).digest())


def _perimeter(width: int, height: int) -> list[WallSegment]:
    return [
        WallSegment(x1=0, y1=0, x2=width, y2=0, wall_type="perimeter"),
        WallSegment(x1=width, y1=0, x2=width, y2=height, wall_type="perimeter"),
        WallSegment(x1=width, y1=height, x2=0, y2=height, wall_type="perimeter"),
        WallSegment(x1=0, y1=height, x2=0, y2=0, wall_type="perimeter"),
    ]


def _vertical_divider(
    grid: list[list[int]], mid_x: int, door_y: int, height: int
) -> tuple[list[WallSegment], list[DoorSegment]]:
    """Wall down the middle with a two-cell door opening at door_y."""
    doors: list[DoorSegment] = []
    for y in range(1, height - 1):
        if y in (door_y, door_y + 1):
            doors.append(DoorSegment(x1=mid_x, y1=y, x2=mid_x + 1, y2=y, state="closed"))
        else:
            grid[y][mid_x] = 1
    walls = [
        WallSegment(x1=mid_x, y1=1, x2=mid_x, y2=door_y, is_door=False),
        WallSegment(x1=mid_x, y1=door_y + 2, x2=mid_x, y2=height - 1, is_door=False),
    ]
    return walls, doors


def _horizontal_divider(
    grid: list[list[int]], mid_x: int, mid_y: int, door_x: int
) -> tuple[list[WallSegment], list[DoorSegment]]:
    """Wall across the left wing with one door at door_x."""
    doors: list[DoorSegment] = []
    for x in range(1, mid_x):
        if x != door_x:
            grid[mid_y][x] = 1
        else:
            doors.append(DoorSegment(x1=x, y1=mid_y, x2=x + 1, y2=mid_y, state="closed"))
    walls = [
        WallSegment(x1=1, y1=mid_y, x2=door_x, y2=mid_y, is_door=False),
        WallSegment(x1=door_x + 1, y1=mid_y, x2=mid_x, y2=mid_y, is_door=False),
    ]
    return walls, doors


def _pillars(
    rng: random.Random,
    grid: list[list[int]],
    mid_x: int,
    width: int,
    height: int,
    wall_density: float,
) -> list[WallSegment]:
    """Place pillars on a coarse lattice in the right wing. Each site uses the seeded draw."""
    walls: list[WallSegment] = []
    step = max(3, int(1 / (wall_density + 0.05)))
    for y in range(2, height - 2, step):
        for x in range(mid_x + 2, width - 2, step):
            if rng.random() < wall_density:
                grid[y][x] = 1
                walls.append(WallSegment(x1=x, y1=y, x2=x + 1, y2=y + 1, wall_type="pillar"))
    return walls


def _hazards(
    grid: list[list[int]],
    mid_x: int,
    width: int,
    height: int,
    hazard_density: float,
    hazard_type: str,
    damage_dice: str,
) -> list[HazardCell]:
    """Lay a hazard canal in the right quadrant. Its length follows hazard_density."""
    cells: list[HazardCell] = []
    target = max(2, int((width * height) * hazard_density * 0.15))
    canal_x = mid_x + max(2, (width - mid_x) // 2)
    for y in range(2, min(height - 2, 2 + target)):
        if grid[y][canal_x] == 0:
            grid[y][canal_x] = 2
            cells.append(
                HazardCell(
                    x=canal_x,
                    y=y,
                    hazard_type=hazard_type,
                    damage_dice=damage_dice,
                    terrain_type="difficult",
                )
            )
    return cells


class DeterministicMapGenerator(MapGenerator):
    """Default generator. Keyword themes, seeded divider doors and pillar placement."""

    generator_name: ClassVar[str] = "deterministic"

    async def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int | None,
        *,
        wall_density: float = 0.2,
        hazard_density: float = 0.1,
        theme_override: str | None = None,
    ) -> MapLayout:
        theme, hazard_type, damage_dice = infer_theme_from_prompt(prompt)
        if theme_override:
            theme = theme_override

        rng = _layout_rng(prompt, seed, width, height)
        grid: list[list[int]] = [[0] * width for _ in range(height)]
        for x in range(width):
            grid[0][x] = 1
            grid[height - 1][x] = 1
        for y in range(height):
            grid[y][0] = 1
            grid[y][width - 1] = 1

        mid_x, mid_y = width // 2, height // 2
        door_y = rng.randint(max(1, mid_y - 2), min(height - 3, mid_y + 2))
        door_x = rng.randrange(1, mid_x)

        walls = _perimeter(width, height)
        v_walls, v_doors = _vertical_divider(grid, mid_x, door_y, height)
        h_walls, h_doors = _horizontal_divider(grid, mid_x, mid_y, door_x)
        walls += v_walls + h_walls
        doors = v_doors + h_doors
        walls += _pillars(rng, grid, mid_x, width, height, wall_density)
        hazards = _hazards(grid, mid_x, width, height, hazard_density, hazard_type, damage_dice)

        return MapLayout(
            theme=theme,
            wall_segments=walls,
            hazard_cells=hazards,
            doors=doors,
            grid=grid,
        )
