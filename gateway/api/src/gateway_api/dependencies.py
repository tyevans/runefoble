"""Shared dependencies, configuration, and state for Gateway API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket
from gateway_api.upstreams import UpstreamRegistry
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from starlette.requests import HTTPConnection

logger = logging.getLogger("runefoble.gateway.dependencies")

platform_settings = PlatformSettings()


event_bus_provider = EventBusProvider(platform_settings)
get_event_bus = event_bus_provider.get
set_event_bus = event_bus_provider.set


class WebSocketConnectionManager:
    """Tracks live session sockets in one group per session.

    A broadcast reaches only the sockets of the named session.
    This manager keeps state in one process. With more than one gateway replica,
    a message reaches only the clients on the replica that handled it.
    """

    def __init__(self) -> None:
        self.session_connections: dict[str, list[WebSocket]] = {}

    def register(self, session_id: str, websocket: WebSocket) -> None:
        """Track an admitted, accepted socket. The route accepts it first."""
        self.session_connections.setdefault(session_id, []).append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        group = self.session_connections.get(session_id)
        if group is None:
            return
        if websocket in group:
            group.remove(websocket)
        if not group:
            del self.session_connections[session_id]

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        for connection in list(self.session_connections.get(session_id, [])):
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001 - one dead peer must not stop the fan-out
                logger.warning("dropping session socket after failed send", exc_info=True)
                self.disconnect(session_id, connection)


ws_manager = WebSocketConnectionManager()


def get_upstreams(connection: HTTPConnection) -> UpstreamRegistry:
    """FastAPI dependency: the service clients built in the gateway lifespan. Works for HTTP and WebSocket."""
    return connection.app.state.upstreams
