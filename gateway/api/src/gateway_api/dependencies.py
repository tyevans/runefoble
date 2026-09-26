"""Shared dependencies, configuration, and state for Gateway API."""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import WebSocket
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus | None:
    """Retrieve or lazily initialize the platform RedisStreamsEventBus."""
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    """Explicitly set or override the event bus instance (e.g. for testing)."""
    global _event_bus
    _event_bus = bus


class WebSocketConnectionManager:
    """Manages active live session WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for connection in self.active_connections:
            with contextlib.suppress(Exception):
                await connection.send_json(message)


ws_manager = WebSocketConnectionManager()
