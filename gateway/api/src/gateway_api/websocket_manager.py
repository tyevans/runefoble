"""Client connection hub and broadcast manager for campaign WebSockets."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("runefoble.gateway.websocket_manager")


class CampaignConnectionManager:
    """Manages active live WebSocket connections and broadcast per campaign."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[tuple[WebSocket, str]]] = {}

    async def connect(self, campaign_id: str, websocket: WebSocket, subject_id: str) -> None:
        """Register active connection for a campaign."""
        if campaign_id not in self.active_connections:
            self.active_connections[campaign_id] = []
        self.active_connections[campaign_id].append((websocket, subject_id))

    def disconnect(self, campaign_id: str, websocket: WebSocket) -> None:
        """Remove active connection for a campaign."""
        if campaign_id in self.active_connections:
            self.active_connections[campaign_id] = [
                (ws, sub) for (ws, sub) in self.active_connections[campaign_id] if ws != websocket
            ]
            if not self.active_connections[campaign_id]:
                del self.active_connections[campaign_id]

    async def broadcast_to_campaign(self, campaign_id: str, message: dict[str, Any]) -> None:
        """Broadcast JSON message payload to all connected party clients in a campaign."""
        for ws, _ in list(self.active_connections.get(campaign_id, [])):
            with contextlib.suppress(Exception):
                await ws.send_json(message)


# Backward-compatible aliases
CampaignWebSocketManager = CampaignConnectionManager
ws_campaign_manager = CampaignConnectionManager()

__all__ = [
    "CampaignConnectionManager",
    "CampaignWebSocketManager",
    "logger",
    "ws_campaign_manager",
]
