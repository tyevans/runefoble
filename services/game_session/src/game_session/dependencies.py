"""Shared dependencies, repository, and event bus for Game Session microservice."""

from __future__ import annotations

import contextlib
import logging
import os

from game_session.aggregate import GameSessionAggregate
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

logger = logging.getLogger("runefoble.game_session")
WATCHER_SERVICE_URL = os.environ.get("RUNEFOBLE_WATCHER_URL")
STREAM_WATCHER = "runefoble.events.watcher"
STREAM_SESSION = "runefoble.events.session"

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None

repo: AggregateRepository[GameSessionAggregate] = create_aggregate_repository(GameSessionAggregate)


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus
