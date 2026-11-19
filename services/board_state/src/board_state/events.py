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


async def save_and_publish(repo: Any, board: Any, bus: RedisStreamsEventBus | None) -> None:
    """Save the board, then publish the events that this write committed.

    Every board write uses this path: the REST routes and the WebSocket confirm. The events are
    read before the save, so a save cannot clear them first.
    """
    uncommitted = list(board.uncommitted_events)
    await repo.save(board)
    if bus is not None:
        await publish_board_events(bus, uncommitted)
