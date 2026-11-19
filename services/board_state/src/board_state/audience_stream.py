"""The board_state consumer of the audience stream (TASK-0835, TASK-0837).

One consumer reads `runefoble.events.audience` and passes each message to every audience
applier of board_state. Each applier ignores the modifier types it does not own, so the
messages of one stream never reach a second consumer with the same group name.

Governed by ADR-0006 (Redis Streams event bus) and ADR-0007 (each owner applies its own effect).
"""

from __future__ import annotations

from typing import Any

from board_state.audience_hazard import apply_audience_hazard_event
from board_state.audience_item_drop import apply_audience_item_drop_event
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer

GROUP_NAME = "board_state_audience_workers"
WORKER_NAME = "board_state_audience_consumer_1"
AUDIENCE_STREAM = "runefoble.events.audience"


def build_audience_consumer(
    consumer_group: RedisConsumerGroup, bus: RedisStreamsEventBus
) -> StreamConsumer:
    """Build the stream consumer for the audience stream. The caller starts it."""

    async def _handle(_message_id: str, event: Any) -> None:
        await apply_audience_hazard_event(event, bus)
        await apply_audience_item_drop_event(event, bus)

    return StreamConsumer(
        consumer_group=consumer_group,
        stream=AUDIENCE_STREAM,
        group_name=GROUP_NAME,
        consumer_name=WORKER_NAME,
        handler=_handle,
    )
