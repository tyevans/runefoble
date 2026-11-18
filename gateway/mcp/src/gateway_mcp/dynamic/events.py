"""System event dispatch and bus helpers for dynamic MCP tools."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from opentelemetry import trace

logger = logging.getLogger("runefoble.gateway_mcp.dynamic.events")
SYSTEM_STREAM = "runefoble.events.system"
_event_bus: Any = None
# Strong references keep fire-and-forget publish tasks alive until they finish.
_pending_publishes: set[asyncio.Task[None]] = set()


def get_event_bus() -> Any:
    """Return the event bus injected at gateway startup. Never falls back to memory."""
    if _event_bus is None:
        raise RuntimeError("Dynamic MCP event bus is not configured; call set_event_bus at startup")
    return _event_bus


def set_event_bus(bus: Any) -> None:
    """Set active event bus singleton."""
    global _event_bus
    _event_bus = bus


def safe_dispatch_event(event: Any) -> None:
    """Schedule event publication on the running loop without blocking the caller."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _record_dropped(event, "no running event loop")
        return
    task = loop.create_task(publish_system_event(event))
    _pending_publishes.add(task)
    task.add_done_callback(_pending_publishes.discard)


async def publish_system_event(event: Any) -> None:
    """Publish domain event to Redis Streams system topic. Failures are logged, not raised."""
    try:
        bus = get_event_bus()
        await bus.publish_event(SYSTEM_STREAM, event)
    except Exception as exc:
        _record_dropped(event, f"{type(exc).__name__}: {exc}")


def _record_dropped(event: Any, reason: str) -> None:
    """Log a dropped event at error level and mark the active trace span."""
    event_type = type(event).__name__
    logger.error("Dropped %s for %s: %s", event_type, SYSTEM_STREAM, reason)
    trace.get_current_span().add_event(
        "dynamic_tool_event_dropped", {"event_type": event_type, "reason": reason}
    )
