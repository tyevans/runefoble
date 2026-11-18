"""Shared dependencies, configuration, and state for Gateway API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, WebSocket
from gateway_api.upstreams import UpstreamRegistry
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider

logger = logging.getLogger("runefoble.gateway.dependencies")

platform_settings = PlatformSettings()


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


class WebSocketConnectionManager:
    """Manages active live session WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    def register(self, websocket: WebSocket) -> None:
        """Track an admitted, accepted socket. The route accepts it first."""
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001 - one dead peer must not stop the fan-out
                logger.warning("dropping session socket after failed send", exc_info=True)
                self.disconnect(connection)


ws_manager = WebSocketConnectionManager()


def get_upstreams(request: Request) -> UpstreamRegistry:
    """FastAPI dependency: the service clients built in the gateway lifespan."""
    return request.app.state.upstreams
