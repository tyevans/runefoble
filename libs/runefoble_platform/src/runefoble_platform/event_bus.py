"""Shared Redis Streams event bus provider with fail-fast start-up (ADR-0015 item 4).

A service that configures Redis must not start when Redis is unreachable. This module
never substitutes an in-memory bus. Each service owns one `EventBusProvider` and exposes
`provider.get` and `provider.set` as its `get_event_bus` and `set_event_bus`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

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


class EventBusProvider:
    """Own one lazily built Redis Streams bus for a service process."""

    def __init__(self, settings: PlatformSettings) -> None:
        self._settings = settings
        self._bus: RedisStreamsEventBus | None = None
        self._owned = False

    def get(self) -> RedisStreamsEventBus:
        """Return the bus. Build it on first use. Raise when Redis is not configured."""
        if self._bus is None:
            self._bus = create_event_bus(self._settings)
            self._owned = True
        return self._bus

    def set(self, bus: RedisStreamsEventBus | None) -> None:
        """Replace the bus. Tests pass a bus over a Redis test double. None resets it."""
        self._bus = bus
        self._owned = False

    async def connect(self) -> RedisStreamsEventBus:
        """Ping Redis at start-up. Raise EventBusUnavailableError when it is unreachable."""
        bus = self.get()
        await connect_event_bus(bus)
        return bus

    async def close(self) -> None:
        """Close the bus that this provider built. A bus set from outside is left open."""
        bus, owned = self._bus, self._owned
        if bus is not None and owned:
            self._bus, self._owned = None, False
            await bus.close()

    @asynccontextmanager
    async def lifespan(self, _app: FastAPI) -> AsyncIterator[None]:
        """FastAPI lifespan: fail start-up when Redis is unreachable, close the bus at shutdown."""
        await self.connect()
        try:
            yield
        finally:
            await self.close()


__all__ = [
    "EventBusProvider",
    "EventBusUnavailableError",
    "connect_event_bus",
    "create_event_bus",
]
