"""Shared dependencies, repository, and event bus for Game Session microservice."""

from __future__ import annotations

import contextlib
import logging
import os

from game_session.aggregate import GameSessionAggregate
from game_session.stronghold import StrongholdAggregate
from runefoble_auth.spicedb import SpiceDBClient
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
STREAM_STRONGHOLD = "runefoble.events.stronghold"

platform_settings = PlatformSettings()
_event_bus: RedisStreamsEventBus | None = None
_spicedb_client: SpiceDBClient = SpiceDBClient()

repo: AggregateRepository[GameSessionAggregate] = create_aggregate_repository(GameSessionAggregate)
stronghold_repo: AggregateRepository[StrongholdAggregate] = create_aggregate_repository(
    StrongholdAggregate
)


def get_stronghold_repository() -> AggregateRepository[StrongholdAggregate]:
    return stronghold_repo


def get_spicedb_client() -> SpiceDBClient:
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient) -> None:
    global _spicedb_client
    _spicedb_client = client


def get_event_bus() -> RedisStreamsEventBus | None:
    global _event_bus
    if _event_bus is None and platform_settings.redis_url:
        with contextlib.suppress(Exception):
            _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus
