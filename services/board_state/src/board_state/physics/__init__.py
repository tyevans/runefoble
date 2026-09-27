"""Tabletop 3D physics, bounding collision meshes, and ballistic simulation."""

from board_state.physics.applier import apply_dice_throw, apply_token_knockback
from board_state.physics.bounds import BoundingBox3D, BoundingCylinder, HeightfieldTerrain
from board_state.physics.simulator import simulate_dice_trajectory, simulate_knockback_trajectory

__all__ = [
    "BoundingBox3D",
    "BoundingCylinder",
    "HeightfieldTerrain",
    "apply_dice_throw",
    "apply_token_knockback",
    "simulate_dice_trajectory",
    "simulate_knockback_trajectory",
]
