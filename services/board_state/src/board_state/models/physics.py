"""Physics simulation request/response schemas and collision state models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PhysicsCollisionState(BaseModel):
    """Snapshot of a physical rigid-body collision on the board."""

    entity_id: str
    entity_type: str = "token"  # "token" | "dice"
    collision_type: str = "wall"  # "wall" | "token" | "boundary" | "terrain_step"
    x: float
    y: float
    z: float = 0.0
    impact_velocity: float = 0.0
    impact_energy: float = 0.0


class DiceSettledState(BaseModel):
    """Snapshot of a settled tumbling die on the tactical board."""

    dice_id: str
    dice_type: str = "d20"
    face_value: int
    settled_x: float
    settled_y: float
    settled_z: float = 0.0
    bounces: int = 0


class SimulateThrowRequest(BaseModel):
    """Request payload for simulating a 3D physical dice roll on the tactical board."""

    dice_id: str | None = None
    dice_type: str = "d20"
    origin_x: float = 0.0
    origin_y: float = 0.0
    origin_z: float = 2.0
    velocity_x: float = 5.0
    velocity_y: float = 5.0
    velocity_z: float = 2.0
    restitution: float = 0.5
    friction: float = 0.3
    seed: int | None = None
    face_value: int | None = None
    target_face_value: int | None = None


class SimulateThrowResponse(BaseModel):
    """Response payload containing settled dice coordinates, bounce count, and final face."""

    dice_id: str
    dice_type: str
    face_value: int
    settled_x: float
    settled_y: float
    settled_z: float
    settled_cell: list[int]
    bounces: int
    trajectory: list[dict[str, float]] = Field(default_factory=list)
    collisions: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "settled"


class KnockbackRequest(BaseModel):
    """Request payload for applying physical knockback impulse to a miniature token."""

    token_id: str
    direction_x: float = 1.0
    direction_y: float = 0.0
    distance_ft: float = 10.0
    mass: float = 1.0
    force: float | None = None


class KnockbackResponse(BaseModel):
    """Response payload detailing knockback trajectory, stopping coordinates, and collisions."""

    token_id: str
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    settled_position: list[int]
    distance_traveled_ft: float
    collided: bool
    collision_type: str | None = None
    collision_point: list[float] | None = None
    impact_energy: float = 0.0
    trajectory: list[dict[str, float]] = Field(default_factory=list)
    elevation: float = 0.0
    status: str = "settled"


class BoardPhysicsTransitionsMixin:
    """State transition helpers for physical collisions and dice settling."""

    def with_physics_collision(
        self: Any,
        entity_id: str,
        entity_type: str,
        collision_type: str,
        x: float,
        y: float,
        z: float = 0.0,
        impact_velocity: float = 0.0,
        impact_energy: float = 0.0,
    ) -> Any:
        col = PhysicsCollisionState(
            entity_id=entity_id,
            entity_type=entity_type,
            collision_type=collision_type,
            x=x,
            y=y,
            z=z,
            impact_velocity=impact_velocity,
            impact_energy=impact_energy,
        )
        recent = (self.recent_collisions + [col])[-10:]
        return self.model_copy(update={"recent_collisions": recent, "last_collision": col})

    def with_dice_settled(
        self: Any,
        dice_id: str,
        dice_type: str,
        face_value: int,
        settled_x: float,
        settled_y: float,
        settled_z: float = 0.0,
        bounces: int = 0,
    ) -> Any:
        ds = DiceSettledState(
            dice_id=dice_id,
            dice_type=dice_type,
            face_value=face_value,
            settled_x=settled_x,
            settled_y=settled_y,
            settled_z=settled_z,
            bounces=bounces,
        )
        return self.model_copy(update={"last_dice_settled": ds})
