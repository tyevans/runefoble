"""Spatial trap trigger evaluation and movement pause kinematics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from board_state.traps.models import SecretTrapState


@dataclass
class TrapBreach:
    """Represents a trap breach event along a movement path."""

    trap: SecretTrapState
    breach_coord: tuple[int, int]
    movement_paused: bool = True
    effective_path: list[tuple[int, int]] = field(default_factory=list)


def is_trap_triggered(trap: SecretTrapState, x: int, y: int) -> bool:
    """Evaluate whether cell (x, y) breaches the trigger zone of an armed trap."""
    if not trap.is_armed or trap.is_sprung or trap.is_disarmed:
        return False

    if trap.trigger_type in ("step", "touch"):
        return trap.x == x and trap.y == y

    if trap.trigger_type == "proximity":
        dx = abs(trap.x - x)
        dy = abs(trap.y - y)
        return max(dx, dy) <= trap.proximity_radius

    return False


def evaluate_trap_collision_on_path(
    path: list[tuple[int, int]],
    traps: Mapping[str, SecretTrapState] | list[SecretTrapState],
) -> TrapBreach | None:
    """Evaluate whether any point along movement path breaches an armed trap.

    Checks steps sequentially after origin. Halts immediately upon first breach,
    returning the breached trap and truncating the path to the breach coordinate.
    """
    if len(path) <= 1:
        return None

    trap_list = traps.values() if isinstance(traps, Mapping) else traps
    effective_path: list[tuple[int, int]] = [path[0]]

    for step in path[1:]:
        effective_path.append(step)
        for trap in trap_list:
            if is_trap_triggered(trap, step[0], step[1]):
                return TrapBreach(
                    trap=trap,
                    breach_coord=step,
                    movement_paused=True,
                    effective_path=list(effective_path),
                )

    return None
