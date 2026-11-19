"""Supervised consumer that sends server session frames from domain events (TASK-0923).

It reads `runefoble.events.session` (dice and turns) and `runefoble.events.watcher` (whispers,
TASK-0927). A DM-only frame goes to the DM socket group only, never to player or spectator
sockets.

Governed by ADR-0006 (Redis Streams), ADR-0011 (domain events) and ADR-0015 (fail loud).

Each gateway replica holds its own session sockets, so each replica must read every event. The
consumer group name includes the host name, which gives one group per replica. A new group starts
at the end of the stream (`$`): a replica does not replay old dice or turns to new sockets.

A stream message can arrive twice (a publisher retry or a reclaim). The replica keeps the ids of
the last `SEEN_EVENT_LIMIT` source events in memory and sends no second frame for one of them.
The ledger is in memory because the sockets are in memory too: a restarted replica has no
sockets that received the earlier frame.
"""

from __future__ import annotations

import logging
import socket
from collections import OrderedDict
from typing import Any

from gateway_api.dependencies import ws_dm_manager, ws_manager
from gateway_api.live_session_frames import live_frame_for
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

logger = logging.getLogger("runefoble.gateway.session_frame_consumer")

SESSION_FRAMES = "session_frames"
SESSION_STREAM = "runefoble.events.session"
WATCHER_STREAM = "runefoble.events.watcher"
SEEN_EVENT_LIMIT = 1000


class SeenEvents:
    """A bounded, ordered set of source event ids that this replica already sent."""

    def __init__(self, limit: int = SEEN_EVENT_LIMIT) -> None:
        self._limit = limit
        self._ids: OrderedDict[str, None] = OrderedDict()

    def first_time(self, event_id: str) -> bool:
        """Record `event_id`. Return False when it was recorded before."""
        if event_id in self._ids:
            return False
        self._ids[event_id] = None
        if len(self._ids) > self._limit:
            self._ids.popitem(last=False)
        return True


class SessionFrameRelay:
    """Turns one decoded stream event into at most one broadcast to its session room."""

    def __init__(self, seen: SeenEvents | None = None) -> None:
        self._seen = seen if seen is not None else SeenEvents()

    async def handle(self, _message_id: str, event: Any) -> None:
        mapped = live_frame_for(event)
        if mapped is None:
            return
        event_id = str(event.event_id)
        if not self._seen.first_time(event_id):
            logger.info("Skipped redelivered event %s; its frame was sent", event_id)
            return
        groups = ws_dm_manager if mapped.dm_only else ws_manager
        await groups.broadcast(mapped.session_id, mapped.frame)


async def _stream_end() -> str:
    return "$"


async def start_session_frame_consumers(bus: RedisStreamsEventBus) -> SupervisedStreamConsumers:
    """Create this replica's consumer group and start the read loop.

    Raises when the group cannot be created, so the gateway does not start.
    """
    replica = socket.gethostname()
    relay = SessionFrameRelay()
    client = await bus.get_client()
    consumers = SupervisedStreamConsumers(
        SESSION_FRAMES,
        [
            StreamConsumer(
                consumer_group=RedisConsumerGroup(client=client),
                stream=stream,
                group_name=f"gateway_session_frames_{replica}",
                consumer_name=f"gateway_{replica}",
                handler=relay.handle,
                resume_position=_stream_end,
            )
            for stream in (SESSION_STREAM, WATCHER_STREAM)
        ],
    )
    await consumers.start()
    return consumers


__all__ = [
    "SEEN_EVENT_LIMIT",
    "SESSION_FRAMES",
    "SESSION_STREAM",
    "WATCHER_STREAM",
    "SeenEvents",
    "SessionFrameRelay",
    "start_session_frame_consumers",
]
