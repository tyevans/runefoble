"""Redis Streams consumer that feeds session, watcher, and character events into Soundscape.

Governed by ADR-0006 (Redis Streams event bus) and ADR-0015 (fail-fast start-up).
"""

from __future__ import annotations

from typing import Any

from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

from soundscape.event_handlers import handle_incoming_domain_event

CONSUMER_NAME = "soundscape"
GROUP_NAME = "soundscape_workers"
WORKER_NAME = "soundscape_consumer_1"
SOUNDSCAPE_STREAMS: tuple[str, ...] = (
    "runefoble.events.session",
    "runefoble.events.watcher",
    "runefoble.events.character",
)


async def _handle_message(_message_id: str, event: Any) -> None:
    await handle_incoming_domain_event(event)


async def start_soundscape_consumers(bus: RedisStreamsEventBus) -> SupervisedStreamConsumers:
    """Create consumer groups and start one read loop per soundscape stream.

    Raises when a consumer group cannot be created, so the service does not start.
    """
    consumer_group = RedisConsumerGroup(client=await bus.get_client())
    consumers = SupervisedStreamConsumers(
        CONSUMER_NAME,
        [
            StreamConsumer(
                consumer_group=consumer_group,
                stream=stream,
                group_name=GROUP_NAME,
                consumer_name=WORKER_NAME,
                handler=_handle_message,
            )
            for stream in SOUNDSCAPE_STREAMS
        ],
    )
    await consumers.start()
    return consumers
