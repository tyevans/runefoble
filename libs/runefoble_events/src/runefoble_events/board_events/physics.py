"""Tactile 3D collisions and physical tumbling dice domain events."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.board.physics_collision")
class PhysicsCollisionOccurred(BaseRunefobleEvent):
    """Emitted when a physical rigid-body collision occurs on the tactical board."""

    event_type: str = "runefoble.events.board.physics_collision"
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    session_id: str = ""
    board_id: str = ""
    entity_id: str
    entity_type: str = "token"
    collision_type: str = "wall"
    x: float
    y: float
    z: float = 0.0
    impact_velocity: float = 0.0
    impact_energy: float = 0.0
    normal_x: float = 0.0
    normal_y: float = 0.0
    normal_z: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.dice.settled")
class DiceSettled(BaseRunefobleEvent):
    """Emitted when physical tumbling dice come to rest on the tactical board."""

    event_type: str = "runefoble.events.dice.settled"
    aggregate_type: str = "BoardState"
    aggregate_id: UUID = Field(default_factory=uuid4)
    session_id: str = ""
    board_id: str = ""
    dice_id: str
    dice_type: str = "d20"
    face_value: int
    settled_x: float
    settled_y: float
    settled_z: float = 0.0
    rotation: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    bounces: int = 0
    trajectory: list[dict[str, float]] = Field(default_factory=list)
