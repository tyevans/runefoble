"""Shared dependencies, engine instances, and event bus for The Watcher service."""

from __future__ import annotations

import logging
import os
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.autonomous_dm import AutonomousDMEngine
from the_watcher.chronicle import ChronicleRecapEngine
from the_watcher.watcher_ai import TheWatcherEngine

logger = logging.getLogger("runefoble.the_watcher")
INFERENCE_URL = os.environ.get("RUNEFOBLE_INFERENCE_URL")

STREAM_WATCHER = "runefoble.events.watcher"
STREAM_BOARD = "runefoble.events.board"

engine = TheWatcherEngine()
chronicle_engine = ChronicleRecapEngine()
autonomous_dm_engine = AutonomousDMEngine()
platform_settings = PlatformSettings()

_event_bus: RedisStreamsEventBus | None = None


def get_event_bus() -> RedisStreamsEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = RedisStreamsEventBus(redis_url=platform_settings.redis_url)
    return _event_bus


def set_event_bus(bus: RedisStreamsEventBus | None) -> None:
    global _event_bus
    _event_bus = bus


def to_uuid(val: str | UUID | None) -> UUID:
    """Deterministically convert a string or UUID into a valid UUID."""
    if val is None:
        return uuid4()
    if isinstance(val, UUID):
        return val
    try:
        return UUID(val)
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(val))
