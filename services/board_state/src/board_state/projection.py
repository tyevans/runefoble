"""Public projection of the board. It removes the DM secret layer for callers without it.

The secret layer is the secret traps, the secret doors, and the secret portals. A caller
who holds `board.view_secret_layer` gets the full state. Every other caller gets the
projection. Routers call these functions for each response that carries board data.
"""

from __future__ import annotations

from typing import Any

from board_state.models import BoardState
from board_state.traps.models import SecretTrapState


def _is_secret_portal(portal: dict[str, Any]) -> bool:
    return bool(portal.get("secret") or portal.get("is_secret"))


def public_traps(traps: dict[str, Any]) -> dict[str, SecretTrapState]:
    """Return the traps a non-DM may see.

    A trap that is not secret is public. A secret trap that has sprung is revealed, so only
    its place and name remain. A secret trap that has not sprung is absent.
    """
    visible: dict[str, SecretTrapState] = {}
    for trap_id, trap in traps.items():
        if not trap.is_secret:
            visible[trap_id] = trap
        elif trap.is_sprung:
            visible[trap_id] = SecretTrapState(
                trap_id=trap.trap_id,
                board_id=trap.board_id,
                name=trap.name,
                x=trap.x,
                y=trap.y,
                trigger_type=trap.trigger_type,
                is_secret=True,
                is_armed=False,
                is_sprung=True,
            )
    return visible


def public_doors(doors: dict[str, Any]) -> dict[str, Any]:
    """Return the doors without the secret ones."""
    return {door_id: door for door_id, door in doors.items() if not door.get("is_secret")}


def public_portals(portals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the portals without the secret ones."""
    return [portal for portal in portals if not _is_secret_portal(portal)]


def project_board(state: BoardState, can_view_secret: bool) -> BoardState:
    """Return the state as the caller may see it."""
    if can_view_secret:
        return state
    return state.model_copy(
        update={
            "traps": public_traps(state.traps),
            "last_trap_sprung": None,
            "doors": public_doors(state.doors),
            "portals": public_portals(state.portals),
        }
    )
