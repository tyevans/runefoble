"""Interactive doors and dynamic lighting handler mixin for BoardAggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from eventsource.domain.decorators import handles
from runefoble_events.uvtt_elements import (
    BoardDoorToggledEvent,
    BoardLightSourcePlacedEvent,
)

if TYPE_CHECKING:
    from board_state.models import BoardState


class DoorsLightsHandlerMixin:
    """Mixin providing interactive door toggling and point light source placement."""

    _state: BoardState | None
    state: BoardState
    aggregate_id: Any
    create_event: Any

    def toggle_door(
        self,
        door_id: str,
        status: str | None = None,
        is_open: bool | None = None,
        toggled_by: str | None = None,
    ) -> dict[str, Any]:
        """Toggle an interactive door or portal state (open/closed/locked)."""
        current_door = self.state.doors.get(door_id, {})
        if not current_door:
            # Check if matching portal in portals list
            for p in self.state.portals:
                if p.get("id") == door_id or p.get("door_id") == door_id:
                    current_door = p
                    break

        if status is not None:
            new_status = status
            new_open = status == "open"
        elif is_open is not None:
            new_open = is_open
            new_status = "open" if is_open else "closed"
        else:
            cur_open = (
                current_door.get("is_open", False)
                or current_door.get("status") == "open"
                or not current_door.get("closed", True)
            )
            new_open = not cur_open
            new_status = "open" if new_open else "closed"

        self.create_event(
            BoardDoorToggledEvent,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            door_id=door_id,
            status=new_status,
            is_open=new_open,
            toggled_by=toggled_by,
        )
        return {"door_id": door_id, "status": new_status, "is_open": new_open}

    def place_light_source(
        self,
        light_id: str | None = None,
        x: float = 0.0,
        y: float = 0.0,
        color_hex: str = "#ffffffff",
        bright_radius: float = 2.5,
        dim_radius: float = 5.0,
        flicker_intensity: float = 0.0,
        intensity: float = 1.0,
        shadows: bool = True,
        placed_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Place a point light source or radiance emitter on the tactical board."""
        lid = light_id or f"light-{uuid4().hex[:8]}"
        self.create_event(
            BoardLightSourcePlacedEvent,
            session_id=str(self.state.session_id),
            board_id=str(self.aggregate_id),
            light_id=lid,
            x=round(x, 3),
            y=round(y, 3),
            color_hex=color_hex,
            bright_radius=round(bright_radius, 2),
            dim_radius=round(dim_radius, 2),
            flicker_intensity=round(flicker_intensity, 2),
            intensity=round(intensity, 2),
            shadows=shadows,
            placed_by=placed_by,
            metadata=metadata or {},
        )
        return lid

    @handles(BoardDoorToggledEvent)
    def _on_door_toggled(self, e: BoardDoorToggledEvent) -> None:
        self._state = self.state.with_door_toggled(
            door_id=e.door_id,
            status=e.status,
            is_open=e.is_open,
        )

    @handles(BoardLightSourcePlacedEvent)
    def _on_light_placed(self, e: BoardLightSourcePlacedEvent) -> None:
        self._state = self.state.with_light_placed(
            {
                "light_id": e.light_id,
                "x": e.x,
                "y": e.y,
                "color_hex": e.color_hex,
                "bright_radius": e.bright_radius,
                "dim_radius": e.dim_radius,
                "flicker_intensity": e.flicker_intensity,
                "intensity": e.intensity,
                "shadows": e.shadows,
                "placed_by": e.placed_by,
                "metadata": e.metadata,
            }
        )
