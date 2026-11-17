"""Telemetry projection worker consuming Redis Streams domain events into PostgreSQL analytical tables.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
"""

from __future__ import annotations

from typing import Any

from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.stream_consumer import StreamConsumer, SupervisedStreamConsumers

from campaign_analytics.event_handlers import (
    AnalyticsEventDispatcher,
    handle_domain_event,
)
from campaign_analytics.storage import CampaignAnalyticsStorage

CONSUMER_NAME = "analytics"
DEFAULT_STREAMS: tuple[str, ...] = (
    "runefoble.events.session",
    "runefoble.events.board",
    "runefoble.events.character",
    "runefoble.events.watcher",
)


class CampaignAnalyticsWorker:
    """Projects domain events from every monitored stream into analytical read-models."""

    def __init__(
        self,
        storage: CampaignAnalyticsStorage,
        consumer_group: RedisConsumerGroup,
        streams: list[str] | str | None = None,
        group_name: str = "campaign_analytics_worker",
        consumer_name: str = "campaign_analytics_consumer_1",
        poll_interval_ms: int = 100,
        dispatcher: AnalyticsEventDispatcher | None = None,
    ) -> None:
        self.storage = storage
        self.dispatcher = dispatcher or AnalyticsEventDispatcher(storage=self.storage)
        self.streams = [streams] if isinstance(streams, str) else list(streams or DEFAULT_STREAMS)
        self.consumers = SupervisedStreamConsumers(
            CONSUMER_NAME,
            [
                StreamConsumer(
                    consumer_group=consumer_group,
                    stream=stream,
                    group_name=group_name,
                    consumer_name=consumer_name,
                    handler=self.handle_event,
                    poll_interval_s=poll_interval_ms / 1000.0,
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

    async def setup_groups(self) -> None:
        """Create consumer groups on every monitored stream. Errors propagate."""
        await self.consumers.ensure_groups()

    async def handle_event(self, event: Any) -> None:
        """Process a single domain event and update analytical read-models."""
        await handle_domain_event(event, self.storage, self.dispatcher)

    async def process_once(self, count: int = 10, block_ms: int = 100) -> int:
        """Poll monitored streams once. Returns the number of messages handled."""
        return await self.consumers.poll_once(count=count, block_ms=block_ms)

    async def start(self) -> None:
        """Create groups, then start the supervised read loops. Raises if a group fails."""
        await self.consumers.start()

    async def stop(self) -> None:
        """Stop the read loops."""
        await self.consumers.stop()
