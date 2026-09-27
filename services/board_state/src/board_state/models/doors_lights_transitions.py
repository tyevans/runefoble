"""Board aggregate state transitions for interactive doors and dynamic point lights."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from board_state.models.board import BoardState


class BoardDoorsLightsTransitionsMixin:
    """Provides pure state mutation helpers for interactive doors and dynamic lights."""

    def with_door_toggled(
        self: BoardState,
        door_id: str,
        status: str,
        is_open: bool,
    ) -> BoardState:
        doors = dict(self.doors)
        existing = dict(doors.get(door_id, {}))
        existing.update(
            {
                "door_id": door_id,
                "status": status,
                "is_open": is_open,
                "closed": not is_open,
                "is_locked": (status == "locked"),
            }
        )
        doors[door_id] = existing

        updated_portals = []
        for p in self.portals:
            p_copy = dict(p)
            if p_copy.get("id") == door_id or p_copy.get("door_id") == door_id:
                p_copy["closed"] = not is_open
                p_copy["status"] = status
            updated_portals.append(p_copy)

        return self.model_copy(update={"doors": doors, "portals": updated_portals})

    def with_light_placed(
        self: BoardState,
        light_data: dict[str, Any],
    ) -> BoardState:
        lid = light_data.get("light_id") or light_data.get("id")
        lights = [
            dict(light_item)
            for light_item in self.lights
            if light_item.get("light_id") != lid and light_item.get("id") != lid
        ]
        lights.append(light_data)
        return self.model_copy(update={"lights": lights})
