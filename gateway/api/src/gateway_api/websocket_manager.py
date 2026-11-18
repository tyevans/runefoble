"""Live campaign sockets: one WebSocket group per campaign."""

from __future__ import annotations

from runefoble_platform.ws_groups import WebSocketGroups

ws_campaign_manager = WebSocketGroups[str]()

__all__ = ["ws_campaign_manager"]
