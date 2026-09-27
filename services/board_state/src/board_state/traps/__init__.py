"""Secret DM traps, trigger layers, and map switching module."""

from board_state.traps.evaluator import (
    TrapBreach,
    evaluate_trap_collision_on_path,
    is_trap_triggered,
)
from board_state.traps.map_switcher import perform_map_switch
from board_state.traps.models import (
    CreateTrapRequest,
    SecretTrapState,
    SwitchMapRequest,
    SwitchMapResponse,
    TrapListResponse,
)

__all__ = [
    "CreateTrapRequest",
    "SecretTrapState",
    "SwitchMapRequest",
    "SwitchMapResponse",
    "TrapBreach",
    "TrapListResponse",
    "evaluate_trap_collision_on_path",
    "is_trap_triggered",
    "perform_map_switch",
]
