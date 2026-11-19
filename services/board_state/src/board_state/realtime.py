"""Live board socket groups: one WebSocket group per board session."""

from __future__ import annotations

from runefoble_platform.ws_groups import WebSocketGroups

board_ws_manager = WebSocketGroups[str]()

__all__ = ["board_ws_manager"]
