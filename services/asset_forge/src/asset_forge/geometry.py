"""Spatial geometry projection: battlemap layout to board_state payloads."""

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
