"""Redis Streams consumers that apply forged battlemaps and audience modifiers to their board (TASK-0704, TASK-0835, TASK-0837).

Governed by ADR-0006 (Redis Streams event bus) and ADR-0015 (fail-fast start-up, no fallbacks).
A handler that raises routes the message to the dead-letter stream. Nothing is applied then.
"""

from __future__ import annotations

from typing import Any

from board_state.audience_stream import build_audience_consumer
from board_state.authz import board_campaign_id
from board_state.dependencies import get_board, repo
from board_state.encounter_consumer import build_encounter_consumer
from board_state.events import save_and_publish
from runefoble_events.asset import BattlemapForged
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

CONSUMER_NAME = "board_state"
GROUP_NAME = "board_state_workers"
WORKER_NAME = "board_state_consumer_1"
FORGE_STREAM = "runefoble.events.asset"


class ForgedBattlemapCampaignError(RuntimeError):
    """Raised when a forged map names a campaign that does not own the target board."""


async def apply_forged_battlemap_event(event: Any, bus: RedisStreamsEventBus | None) -> None:
    """Apply one forged battlemap to the board of its session.

    A map forged without a session has no board, so there is nothing to apply. The asset
    stream also carries other forge events. Those are not this consumer's concern.
    """
    if not isinstance(event, BattlemapForged) or event.session_id is None:
        return
    board = await get_board(event.session_id)
    owner = await board_campaign_id(event.session_id)
    if owner != str(event.campaign_id):
        raise ForgedBattlemapCampaignError(
            f"Forged map {event.asset_id} belongs to campaign {event.campaign_id}, "
            f"not to the campaign of board {event.session_id}."
        )
    if board.state.forged_asset_id == event.asset_id:
        # A redelivery. This map already sets the board geometry, so nothing changes.
        return
    board.apply_forged_battlemap(
        asset_id=event.asset_id,
        cols=event.width_cells,
        rows=event.height_cells,
        wall_segments=event.wall_segments,
        hazard_cells=event.hazard_cells,
    )
    await save_and_publish(repo, board, bus)


async def start_board_consumers(bus: RedisStreamsEventBus) -> SupervisedStreamConsumers:
    """Start the board_state consumers: the forge asset, audience, and encounter streams.

    Raises when the consumer group cannot be created, so the service does not start.
    """
    consumer_group = RedisConsumerGroup(client=await bus.get_client())

    async def _handle(_message_id: str, event: Any) -> None:
        await apply_forged_battlemap_event(event, bus)

    consumers = SupervisedStreamConsumers(
        CONSUMER_NAME,
        [
            StreamConsumer(
                consumer_group=consumer_group,
                stream=FORGE_STREAM,
                group_name=GROUP_NAME,
                consumer_name=WORKER_NAME,
                handler=_handle,
            ),
            build_audience_consumer(consumer_group, bus),
            build_encounter_consumer(consumer_group, bus),
        ],
    )
    await consumers.start()
    return consumers
