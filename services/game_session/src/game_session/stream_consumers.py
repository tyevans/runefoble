"""The supervised Redis Streams consumers of game_session, started in the service lifespan.

- `runefoble.events.audience`: approved weather modifiers (`apply_audience_weather_event`).
- `runefoble.events.board`: token moves for the session chronicle (`chronicle_board_move`).

Each handler that raises routes its message to `{stream}.dlq` (ADR-0006, ADR-0015).
"""

from __future__ import annotations

from typing import Any

from game_session.audience_weather import AUDIENCE_STREAM, apply_audience_weather_event
from game_session.board_moves import BOARD_STREAM, chronicle_board_move
from game_session.play.repositories import PlayRepositories
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

CONSUMER_NAME = "game_session"
GROUP_NAME = "game_session_workers"
WORKER_NAME = "game_session_consumer_1"


async def start_stream_consumers(
    bus: RedisStreamsEventBus, play: PlayRepositories
) -> SupervisedStreamConsumers:
    """Create the consumer groups and start the read loops on the audience and board streams.

    Raises when a consumer group cannot be created, so the service does not start.
    """
    consumer_group = RedisConsumerGroup(client=await bus.get_client())

    async def _weather(_message_id: str, event: Any) -> None:
        await apply_audience_weather_event(event, play.sessions)

    async def _board_move(_message_id: str, event: Any) -> None:
        await chronicle_board_move(event, play.sessions)

    consumers = SupervisedStreamConsumers(
        CONSUMER_NAME,
        [
            StreamConsumer(
                consumer_group=consumer_group,
                stream=stream,
                group_name=GROUP_NAME,
                consumer_name=WORKER_NAME,
                handler=handler,
            )
            for stream, handler in ((AUDIENCE_STREAM, _weather), (BOARD_STREAM, _board_move))
        ],
    )
    await consumers.start()
    return consumers
