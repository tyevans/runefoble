"""Spatial geometry projection: battlemap layout to board_state payloads.

The forge returns layout only. Hazard types and wall segments go to board_state. board_state
owns the hazard damage table and the obstacle rule, so this module sends no damage dice and
no obstacle tokens.
"""

from __future__ import annotations

from typing import Any

from asset_forge.models import (
    BoardGeometryPayload,
    DoorSegment,
    HazardCell,
    WallSegment,
)


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
        }
        for h in hazard_cells
    ]

    return BoardGeometryPayload(
        terrain_mutations=terrain_mutations,
        wall_segments=[w.model_dump() for w in wall_segments],
        doors=[d.model_dump() for d in doors],
    )
