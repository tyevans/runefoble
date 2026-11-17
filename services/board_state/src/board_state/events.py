"""Single publishing path for Board State domain events onto the Redis event bus."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.redis_bus import RedisStreamsEventBus

BOARD_EVENTS_STREAM = "runefoble.events.board"


async def publish_board_events(bus: RedisStreamsEventBus, events: Iterable[Any]) -> None:
    """Publish each event, in order, to the board stream.

    Board routes save state before they publish. A failed publish raises
    DomainEventPublishError, which the app maps to HTTP 503 so the client retries.
    """
    for evt in events:
        await publish_or_fail(bus, BOARD_EVENTS_STREAM, evt)
