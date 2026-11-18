"""Shared Redis Streams event bus factory with fail-fast start-up (ADR-0015 item 4).

A service that configures Redis must not start when Redis is unreachable. This module
never substitutes an in-memory bus.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus


class EventBusUnavailableError(RuntimeError):
    """Raised when the Redis event bus is not configured or cannot be reached."""


def create_event_bus(settings: PlatformSettings) -> RedisStreamsEventBus:
    """Build the Redis Streams bus from settings. The connection opens lazily."""
    if not settings.redis_url:
        raise EventBusUnavailableError("RUNEFOBLE_REDIS_URL is empty; the event bus cannot start.")
    return RedisStreamsEventBus(redis_url=str(settings.redis_url))


async def connect_event_bus(bus: RedisStreamsEventBus) -> None:
    """Open the Redis connection and ping it. Raise EventBusUnavailableError on failure."""
    try:
        client = await bus.get_client()
        await client.ping()
    except Exception as exc:
        await bus.close()
        raise EventBusUnavailableError(
            f"Redis event bus is unreachable at start-up: {type(exc).__name__}: {exc}"
        ) from exc


@asynccontextmanager
async def event_bus_lifespan(
    app: FastAPI, settings: PlatformSettings | None = None
) -> AsyncIterator[RedisStreamsEventBus]:
    """Connect the bus at start-up, store it on app.state, and close it at shutdown."""
    bus = create_event_bus(settings or PlatformSettings())
    await connect_event_bus(bus)
    app.state.event_bus = bus
    try:
        yield bus
    finally:
        app.state.event_bus = None
        await bus.close()


def get_event_bus(request: Request) -> RedisStreamsEventBus:
    """FastAPI dependency: the bus that the app lifespan connected."""
    bus: RedisStreamsEventBus | None = getattr(request.app.state, "event_bus", None)
    if bus is None:
        raise EventBusUnavailableError("The event bus is not started for this application.")
    return bus


__all__ = [
    "EventBusUnavailableError",
    "connect_event_bus",
    "create_event_bus",
    "event_bus_lifespan",
    "get_event_bus",
]
