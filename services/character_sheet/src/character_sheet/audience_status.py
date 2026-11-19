"""Redis Streams consumer that applies an approved audience status modifier to a character (TASK-0836).

Governed by ADR-0006 (Redis Streams event bus), ADR-0007 (each owner applies its own effect),
ADR-0011 (state changes go through the CharacterAggregate), and ADR-0015 (fail loud).
Only `status_buff` modifiers that the DM approved are applied here. Other modifier types
belong to other owners. A handler that raises routes the message to the dead-letter stream.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from character_sheet.dependencies import repo
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.audience_modifiers import (
    approved_modifier,
    parameter,
    refusal,
    require_same_campaign,
    text_parameter,
)
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

CONSUMER_NAME = "character_sheet"
GROUP_NAME = "character_sheet_workers"
WORKER_NAME = "character_sheet_consumer_1"
AUDIENCE_STREAM = "runefoble.events.audience"
STATUS_BUFF_MODIFIER = "status_buff"
# The buff conditions a DM may grant through the audience. Any other name is refused (ADR-0015).
STATUS_BUFF_CONDITIONS = frozenset({"blessed", "inspired"})


async def apply_audience_status_event(event: Any) -> None:
    """Apply the buff condition to the character named in the modifier.

    A rejected proposal (`approved` is not true) and any other modifier type are ignored.
    A missing or unknown character id, condition, or character raises, so the message is
    dead-lettered. A character outside the campaign of the modifier also raises.
    """
    modifier = approved_modifier(event, STATUS_BUFF_MODIFIER)
    if modifier is None:
        return
    raw_character = parameter(modifier, "character_id")
    try:
        character_id = UUID(str(raw_character))
    except ValueError as exc:
        raise refusal(modifier, "names a character id that is not a UUID.") from exc
    condition = text_parameter(modifier, "condition").strip().lower()
    if condition not in STATUS_BUFF_CONDITIONS:
        raise refusal(modifier, f"names unknown condition '{condition}'.")
    character = await load_if_exists(repo, character_id)
    if character is None:
        raise refusal(modifier, f"names unknown character {character_id}.")
    require_same_campaign(modifier, character.state.campaign_id, f"character {character_id}")
    character.apply_condition(condition, source=f"audience:{modifier.proposal_id}")
    await repo.save(character)


async def start_audience_status_consumers(bus: RedisStreamsEventBus) -> SupervisedStreamConsumers:
    """Create the consumer group and start the read loop on the audience stream.

    Raises when the consumer group cannot be created, so the service does not start.
    """
    consumer_group = RedisConsumerGroup(client=await bus.get_client())

    async def _handle(_message_id: str, event: Any) -> None:
        await apply_audience_status_event(event)

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
