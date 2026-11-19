"""Spectator camera focus event. The board owner records where the broadcast camera points."""

from __future__ import annotations

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.board.camera_focused")
class CameraFocused(BaseRunefobleEvent):
    event_type: str = "runefoble.events.board.camera_focused"

    aggregate_type: str = "BoardState"
    target_x: float
    target_y: float
    zoom: float
    duration_ms: int
    easing: str
    reason: str
    active_token_id: str | None = None
    active_character_id: str | None = None
    focused_at: str = ""
