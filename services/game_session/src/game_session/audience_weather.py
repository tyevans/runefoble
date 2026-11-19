"""Redis Streams consumer that applies an approved audience weather modifier to a session (TASK-0441).

Governed by ADR-0006 (Redis Streams event bus), ADR-0007 (each owner applies its own effect),
ADR-0011 (state changes go through the GameSession aggregate), and ADR-0015 (fail loud).
Only `weather_change` modifiers that the DM approved are applied here. Other modifier types
belong to other owners. A handler that raises routes the message to the dead-letter stream.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from game_session.dependencies import repo
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.audience_modifiers import (
    approved_modifier,
    refusal,
    require_same_campaign,
    text_parameter,
)
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

CONSUMER_NAME = "game_session"
GROUP_NAME = "game_session_workers"
WORKER_NAME = "game_session_consumer_1"
AUDIENCE_STREAM = "runefoble.events.audience"
WEATHER_MODIFIER = "weather_change"


async def apply_audience_weather_event(event: Any) -> None:
    """Record the approved weather on the session of the modifier.

    A rejected proposal (`approved` is not true) and any other modifier type are ignored.
    A missing weather value or a missing session raises, so the message is dead-lettered.
    """
    modifier = approved_modifier(event, WEATHER_MODIFIER)
    if modifier is None:
        return
    weather = text_parameter(modifier, "weather")
    if modifier.session_id is None:
        raise refusal(modifier, "has no session.")
    try:
        session_id = UUID(str(modifier.session_id))
    except ValueError as exc:
        raise refusal(modifier, "names a session id that is not a UUID.") from exc
    session = await load_if_exists(repo, session_id)
    if session is None:
        raise refusal(modifier, f"names unknown session {session_id}.")
    require_same_campaign(modifier, session.state.campaign_id, f"session {session_id}")
    proposal_id = str(modifier.proposal_id)
    if session.state.weather_source_proposal_id == proposal_id:
        # A redelivery. This proposal already set the weather, so nothing changes.
        return
    session.apply_weather(weather=weather, source_proposal_id=proposal_id)
    await repo.save(session)


async def start_audience_consumers(bus: RedisStreamsEventBus) -> SupervisedStreamConsumers:
    """Create the consumer group and start the read loop on the audience stream.

    Raises when the consumer group cannot be created, so the service does not start.
    """
    consumer_group = RedisConsumerGroup(client=await bus.get_client())

    async def _handle(_message_id: str, event: Any) -> None:
        await apply_audience_weather_event(event)

    consumers = SupervisedStreamConsumers(
        CONSUMER_NAME,
        [
            StreamConsumer(
                consumer_group=consumer_group,
                stream=AUDIENCE_STREAM,
                group_name=GROUP_NAME,
                consumer_name=WORKER_NAME,
                handler=_handle,
            )
        ],
    )
    await consumers.start()
    return consumers
