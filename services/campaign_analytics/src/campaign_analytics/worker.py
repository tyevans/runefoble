"""Telemetry projection worker consuming Redis Streams domain events into PostgreSQL read models.

Each stream resumes from the position stored with its read model. A message is projected in
one transaction with that position. A failed message raises, so it is never counted as
projected.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
"""

from __future__ import annotations

from functools import partial
from typing import Any

from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

from campaign_analytics.aggregate import CampaignChronicleAggregate
from campaign_analytics.event_handlers import AnalyticsEventDispatcher
from campaign_analytics.storage import CampaignAnalyticsStorage

CONSUMER_NAME = "analytics"
DEFAULT_STREAMS: tuple[str, ...] = (
    "runefoble.events.session",
    "runefoble.events.board",
    "runefoble.events.character",
    "runefoble.events.watcher",
)


class CampaignAnalyticsWorker:
    """Projects domain events from every monitored stream into analytical read models."""

    def __init__(
        self,
        storage: CampaignAnalyticsStorage,
        consumer_group: RedisConsumerGroup,
        chronicle: AggregateRepository[CampaignChronicleAggregate],
        streams: list[str] | str | None = None,
        group_name: str = "campaign_analytics_worker",
        consumer_name: str = "campaign_analytics_consumer_1",
        poll_interval_ms: int = 100,
    ) -> None:
        self.storage = storage
        self.dispatcher = AnalyticsEventDispatcher(chronicle=chronicle)
        self.streams = [streams] if isinstance(streams, str) else list(streams or DEFAULT_STREAMS)
        self.consumers = SupervisedStreamConsumers(
            CONSUMER_NAME,
            [
                StreamConsumer(
                    consumer_group=consumer_group,
                    stream=stream,
                    group_name=group_name,
                    consumer_name=consumer_name,
                    handler=partial(self.handle_event, stream),
                    poll_interval_s=poll_interval_ms / 1000.0,
                    resume_position=partial(storage.stream_position, stream),
                )
                for stream in self.streams
            ],
        )

    @property
    def processed_count(self) -> int:
        return self.consumers.processed_count

    @property
    def status(self) -> str:
        return self.consumers.status

    async def handle_event(self, stream: str, message_id: str, event: Any) -> None:
        """Project one stream message in a transaction that also records its position."""
        async with self.storage.projection(stream, message_id) as tx:
            await self.dispatcher.dispatch(event, tx)

    async def start(self) -> None:
        """Create groups, resume each stream from its stored position, then start the loops.

        Raises if a group cannot be created or a stored position cannot be restored.
        """
        await self.consumers.start()

    async def stop(self) -> None:
        """Stop the read loops."""
        await self.consumers.stop()
