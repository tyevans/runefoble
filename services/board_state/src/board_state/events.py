"""Single publishing path for Board State domain events onto the Redis event bus."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from runefoble_platform.redis_bus import RedisStreamsEventBus

logger = logging.getLogger("runefoble.board_state.events")

BOARD_EVENTS_STREAM = "runefoble.events.board"


async def publish_board_events(bus: RedisStreamsEventBus, events: Iterable[Any]) -> None:
    """Publish each event, in order, to the board stream via ``publish_event``.

    Failures are logged with the stream and event type, then re-raised.
    """
    for evt in events:
        try:
            await bus.publish_event(BOARD_EVENTS_STREAM, evt)
        except Exception:
            logger.exception(
                "Failed to publish %s to stream %s",
                type(evt).__name__,
                BOARD_EVENTS_STREAM,
            )
            raise
