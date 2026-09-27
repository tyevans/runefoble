"""Physics impulses, collisions, and tumbling dice handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.events import DiceSettled, PhysicsCollisionOccurred

if TYPE_CHECKING:
    from board_state.models import BoardState


class PhysicsHandlerMixin:
    """Mixin providing collision impulse tracking and tumbling dice settling for BoardAggregate."""

    _state: BoardState | None
    state: BoardState
    aggregate_id: Any
    create_event: Any

    @handles(PhysicsCollisionOccurred)
    def _on_physics_collision(self, event: PhysicsCollisionOccurred) -> None:
        self._state = self.state.with_physics_collision(
            entity_id=event.entity_id,
            entity_type=event.entity_type,
            collision_type=event.collision_type,
            x=event.x,
            y=event.y,
            z=event.z,
            impact_velocity=event.impact_velocity,
            impact_energy=event.impact_energy,
        )

    @handles(DiceSettled)
    def _on_dice_settled(self, event: DiceSettled) -> None:
        self._state = self.state.with_dice_settled(
            dice_id=event.dice_id,
            dice_type=event.dice_type,
            face_value=event.face_value,
            settled_x=event.settled_x,
            settled_y=event.settled_y,
            settled_z=event.settled_z,
            bounces=event.bounces,
        )
