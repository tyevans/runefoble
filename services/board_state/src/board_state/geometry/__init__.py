"""Grid geometry: cell centres and AoE containment in feet. The single source of spatial rules."""

from board_state.geometry.containment import (
    cell_in_shape,
    cells_as_set,
    cells_in_shape,
    point_in_shape,
)
from board_state.geometry.grid import FT_PER_CELL, cell_centre_ft

__all__ = [
    "FT_PER_CELL",
    "cell_centre_ft",
    "cell_in_shape",
    "cells_as_set",
    "cells_in_shape",
    "point_in_shape",
]
