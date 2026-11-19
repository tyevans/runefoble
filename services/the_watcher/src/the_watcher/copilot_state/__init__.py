"""Event-sourced aggregates for DM pending actions, whispers, and disambiguations (TASK-0568)."""

from the_watcher.copilot_state.errors import (
    CopilotStateError,
    PendingActionNotFoundError,
    PendingActionStateError,
    WhisperNotFoundError,
    WhisperStateError,
    install_copilot_state_error_handlers,
)

__all__ = [
    "CopilotStateError",
    "PendingActionNotFoundError",
    "PendingActionStateError",
    "WhisperNotFoundError",
    "WhisperStateError",
    "install_copilot_state_error_handlers",
]
