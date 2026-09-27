"""System event dispatch and bus helpers for dynamic MCP tools."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("runefoble.gateway_mcp.dynamic.events")
SYSTEM_STREAM = "runefoble:events:system"
_event_bus: Any = None


def get_event_bus() -> Any:
    """Retrieve event bus singleton, falling back to mock Redis bus."""
    global _event_bus
    if _event_bus is None:
        try:
            from runefoble_platform.consumer_group import MockAsyncRedis
            from runefoble_platform.redis_bus import RedisStreamsEventBus

            _event_bus = RedisStreamsEventBus(client=MockAsyncRedis())
        except Exception:
            _event_bus = None
    return _event_bus


def set_event_bus(bus: Any) -> None:
    """Set active event bus singleton."""
    global _event_bus
    _event_bus = bus


def safe_dispatch_event(event: Any) -> None:
    """Safely dispatch event to active event loop without blocking."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(publish_system_event(event))
    except RuntimeError:
        pass


async def publish_system_event(event: Any) -> None:
    """Publish domain event to Redis Streams system topic."""
    try:
        bus = get_event_bus()
        if bus:
            await bus.publish_event(SYSTEM_STREAM, event)
    except Exception as exc:
        logger.debug("Failed publishing %s: %s", type(event).__name__, exc)
