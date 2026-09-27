"""Collision boundaries, bounding volumes, and heightfield terrain collision structures."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BoundingBox3D:
    """Axis-aligned 3D bounding box for table limits and collision boundaries."""

    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    def contains(self, x: float, y: float, z: float) -> bool:
        return (
            self.min_x <= x <= self.max_x
            and self.min_y <= y <= self.max_y
            and self.min_z <= z <= self.max_z
        )

    def intersects(self, other: BoundingBox3D) -> bool:
        return (
            self.min_x <= other.max_x
            and self.max_x >= other.min_x
            and self.min_y <= other.max_y
            and self.max_y >= other.min_y
            and self.min_z <= other.max_z
            and self.max_z >= other.min_z
        )


@dataclass
class BoundingCylinder:
    """Upright cylindrical collision mesh for miniature tokens."""

    center_x: float
    center_y: float
    base_z: float = 0.0
    height: float = 1.8
    radius: float = 0.4
    token_id: str = ""

    def contains(self, x: float, y: float, z: float) -> bool:
        if not (self.base_z <= z <= self.base_z + self.height):
            return False
        return (x - self.center_x) ** 2 + (y - self.center_y) ** 2 <= self.radius**2

    def intersects(self, other: BoundingCylinder) -> bool:
        z_overlap = max(self.base_z, other.base_z) <= min(
            self.base_z + self.height, other.base_z + other.height
        )
        if not z_overlap:
            return False
        dist_sq = (self.center_x - other.center_x) ** 2 + (self.center_y - other.center_y) ** 2
        return dist_sq <= (self.radius + other.radius) ** 2


@dataclass
class HeightfieldTerrain:
    """Heightfield elevation grid and discrete obstacle registry for tactical boards."""

    cols: int = 12
    rows: int = 12
    elevation_map: dict[tuple[int, int], float] = field(default_factory=dict)
    wall_cells: set[tuple[int, int]] = field(default_factory=set)
    token_cylinders: dict[str, BoundingCylinder] = field(default_factory=dict)

    def elevation_at(self, x: float, y: float) -> float:
        cx, cy = int(math.floor(x)), int(math.floor(y))
        return self.elevation_map.get((cx, cy), 0.0)

    def is_out_of_bounds(self, x: float, y: float) -> bool:
        return x < 0.0 or x >= float(self.cols) or y < 0.0 or y >= float(self.rows)

    def is_wall_or_cliff(
        self, from_x: float, from_y: float, to_x: float, to_y: float, max_step: float = 0.5
    ) -> bool:
        tcx, tcy = int(math.floor(to_x)), int(math.floor(to_y))
        if (tcx, tcy) in self.wall_cells:
            return True
        from_elev = self.elevation_at(from_x, from_y)
        to_elev = self.elevation_at(to_x, to_y)
        return (to_elev - from_elev) > max_step

    def check_token_collision(
        self, x: float, y: float, z: float, ignore_token_id: str | None = None
    ) -> str | None:
        for tid, cyl in self.token_cylinders.items():
            if tid != ignore_token_id and cyl.contains(x, y, z):
                return tid
        return None

    @classmethod
    def from_board_state(cls, board_state: Any) -> HeightfieldTerrain:
        elev_map: dict[tuple[int, int], float] = {}
        for key, cell in board_state.terrain_cells.items():
            cx, cy = (key if isinstance(key, tuple) else tuple(map(int, str(key).split(","))))[:2]
            elev_map[(cx, cy)] = float(getattr(cell, "elevation", 0))

        wall_cells: set[tuple[int, int]] = set()
        token_cyls: dict[str, BoundingCylinder] = {}
        for tid, tok in board_state.tokens.items():
            if getattr(tok, "token_type", "") == "obstacle":
                wall_cells.add((tok.x, tok.y))
            else:
                elev = elev_map.get((tok.x, tok.y), 0.0)
                token_cyls[str(tid)] = BoundingCylinder(
                    center_x=float(tok.x) + 0.5,
                    center_y=float(tok.y) + 0.5,
                    base_z=elev,
                    height=1.8,
                    radius=0.4,
                    token_id=str(tid),
                )
        return cls(
            cols=board_state.cols,
            rows=board_state.rows,
            elevation_map=elev_map,
            wall_cells=wall_cells,
            token_cylinders=token_cyls,
        )
