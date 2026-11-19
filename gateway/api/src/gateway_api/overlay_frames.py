"""Inbound frame schema for the overlay and spectator sockets (G-12).

A frame that does not match this model is refused with an `INVALID_FRAME` error frame. The
socket stays open, and nothing is broadcast.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

TURN_STARTED_ACTIONS = ("turn_started", "runefoble.events.session.turn_started")
TOKEN_MOVED_ACTIONS = ("token_moved", "move_token", "runefoble.events.board.token_moved")
ROLL_ACTIONS = ("dice_rolled", "roll_animation")


class OverlayFrame(BaseModel):
    """One inbound frame. Keys that the schema does not name are ignored."""

    model_config = ConfigDict(extra="ignore")

    action: str | None = None
    type: str | None = None
    token_id: str | None = None
    character_id: str | None = None
    to_x: int | None = None
    to_y: int | None = None
    duration_ms: int | None = None
    easing: str | None = None
    roller_name: str = "Adventurer"
    dice_formula: str = "1d20"
    result: int = 0
    is_critical: bool = False
    is_fumble: bool = False


def frame_kind(data: Any) -> str:
    """Return the action name of a raw frame, or `unknown` when the frame has none."""
    if not isinstance(data, dict):
        return "unknown"
    return str(data.get("action") or data.get("type") or "unknown")


__all__ = [
    "ROLL_ACTIONS",
    "TOKEN_MOVED_ACTIONS",
    "TURN_STARTED_ACTIONS",
    "OverlayFrame",
    "frame_kind",
]
