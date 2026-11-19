"""Campaign socket actions and the owner route that performs each one (TASK-0883).

The table `ACTIONS` maps each action name to a builder. A builder reads the frame and returns
the owner route and the body. The socket sends the call with the caller's token. The owner
checks the token and every object permission, and it publishes its own domain event. The
gateway holds no permission policy and publishes no event (ADR-0015 b, Hard Invariant 2).

An action that is not in `ACTIONS` has no owner route, so the socket refuses it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from runefoble_platform.service_client import OwnerRoute, owner_routes

MOVE_FIELDS = ("to_x", "to_y", "initiated_by", "movement_budget")
MONSTER_FIELDS = ("x", "y", "hp", "is_friendly")
LIGHT_FIELDS = (
    "light_id",
    "x",
    "y",
    "color_hex",
    "bright_radius",
    "dim_radius",
    "flicker_intensity",
    "intensity",
    "shadows",
    "metadata",
)


@dataclass(frozen=True)
class OwnerCall:
    """One call to an owner: the owning service, its route, and the JSON body (or None)."""

    service: str
    route: OwnerRoute
    body: dict[str, Any] | None = None


Builder = Callable[[str, dict[str, Any]], OwnerCall]
"""Build the owner call from the frame session id and the frame. Raise ValueError when a value is missing."""


def _fields(frame: dict[str, Any], names: tuple[str, ...]) -> dict[str, Any]:
    """Copy only the named fields that the frame carries. The owner validates their types."""
    return {name: frame[name] for name in names if name in frame}


def _required(frame: dict[str, Any], name: str) -> str:
    value = frame.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"frame needs a non-empty '{name}'")
    return value


def _move_token(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    token_id = _required(frame, "token_id")
    route = owner_routes.move_token(session_id, token_id)
    return OwnerCall("board_state", route, _fields(frame, MOVE_FIELDS))


def _modify_hp(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    route = owner_routes.change_health(_required(frame, "character_id"))
    return OwnerCall("character_sheet", route, _fields(frame, ("delta", "source")))


def _apply_condition(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    route = owner_routes.apply_condition(_required(frame, "character_id"))
    body = _fields(frame, ("condition", "duration_rounds", "source"))
    return OwnerCall("character_sheet", route, body)


def _clear_condition(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    route = owner_routes.clear_condition(
        _required(frame, "character_id"), _required(frame, "condition")
    )
    return OwnerCall("character_sheet", route)


def _spawn_monster(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    """A monster is a board token of type `monster`. The owner checks `board.manage_traps`."""
    body = _fields(frame, MONSTER_FIELDS)
    body["name"] = frame.get("monster_name")
    body["token_type"] = "monster"
    return OwnerCall("board_state", owner_routes.place_token(session_id), body)


def _end_session(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    return OwnerCall("game_session", owner_routes.end_session(session_id))


def _toggle_door(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    route = owner_routes.toggle_door(session_id, _required(frame, "door_id"))
    return OwnerCall("board_state", route, _fields(frame, ("status", "is_open")) or None)


def _place_light(session_id: str, frame: dict[str, Any]) -> OwnerCall:
    return OwnerCall(
        "board_state", owner_routes.place_light(session_id), _fields(frame, LIGHT_FIELDS)
    )


ACTIONS: Mapping[str, Builder] = {
    "move_token": _move_token,
    "modify_hp": _modify_hp,
    "apply_condition": _apply_condition,
    "clear_condition": _clear_condition,
    "spawn_monster": _spawn_monster,
    "end_session": _end_session,
    "toggle_door": _toggle_door,
    "place_light": _place_light,
}

__all__ = ["ACTIONS", "OwnerCall"]
