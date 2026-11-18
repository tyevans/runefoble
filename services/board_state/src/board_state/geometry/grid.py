"""Cell centre conversion for square and hex grids. One cell spans 5 feet."""

from __future__ import annotations

import math

FT_PER_CELL = 5.0


def cell_centre_ft(col: int, row: int, grid_type: str = "square") -> tuple[float, float]:
    """Return the centre of cell (col, row) in feet."""
    if grid_type == "hex":
        # Pointy-topped hex: column spacing is 5 * sqrt(3) / 2, row spacing is 5 * 0.75.
        col_offset = 0.5 if row % 2 == 1 else 0.0
        centre_x = (col + 0.5 + col_offset) * (FT_PER_CELL * math.sqrt(3) / 2.0)
        centre_y = (row + 0.5) * (FT_PER_CELL * 0.75)
        return centre_x, centre_y
    return (col + 0.5) * FT_PER_CELL, (row + 0.5) * FT_PER_CELL
