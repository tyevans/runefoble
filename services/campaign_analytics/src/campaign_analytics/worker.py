"""Telemetry projection worker consuming Redis Streams domain events into PostgreSQL analytical tables.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from runefoble_platform.consumer_group import RedisConsumerGroup

from campaign_analytics.event_handlers import (
    AnalyticsEventDispatcher,
    handle_domain_event,
)
from campaign_analytics.storage import CampaignAnalyticsStorage

logger = logging.getLogger("runefoble.campaign_analytics.worker")


class CampaignAnalyticsWorker:
    """Asynchronous background worker coordinating Redis Streams polling and analytical event projection."""

    def __init__(
        self,
        storage: CampaignAnalyticsStorage,
        consumer_group: RedisConsumerGroup | None = None,
        streams: list[str] | str | None = None,
        group_name: str = "campaign_analytics_worker",
        consumer_name: str = "campaign_analytics_consumer_1",
        poll_interval_ms: int = 100,
        dispatcher: AnalyticsEventDispatcher | None = None,
    ) -> None:
        self.storage = storage
        self.consumer_group = consumer_group
        default_streams = [
            "runefoble.events.session",
            "runefoble.events.board",
            "runefoble.events.character",
            "runefoble.events.watcher",
        ]
        self.streams = [streams] if isinstance(streams, str) else list(streams or default_streams)
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.poll_interval_ms = poll_interval_ms
        self.running: bool = False
        self._task: asyncio.Task[None] | None = None
        self.processed_count: int = 0
        self.dispatcher = dispatcher or AnalyticsEventDispatcher(storage=self.storage)

    async def setup_groups(self) -> None:
        """Ensure consumer groups exist across all monitored streams."""
        if not self.consumer_group:
            return
        for stream in self.streams:
            with contextlib.suppress(Exception):
                await self.consumer_group.create_group(
                    stream=stream,
                    group_name=self.group_name,
                    start_id="0",
                    make_stream=True,
                )

    async def handle_event(self, event: Any) -> None:
        """Process a single domain event and update analytical read-models."""
        await handle_domain_event(event, self.storage, self.dispatcher)

    async def process_once(self, count: int = 10, block_ms: int = 100) -> int:
        """Poll monitored streams once and apply projection events."""
        if not self.consumer_group:
            return 0
        total = 0
        for stream in self.streams:
            try:
                entries = await self.consumer_group.read_group(
                    stream=stream,
                    group_name=self.group_name,
                    consumer_name=self.consumer_name,
                    count=count,
                    block_ms=block_ms,
                )
            except Exception as e:
                logger.debug("read_group on %s: %s", stream, e)
                continue

            for msg_id, payload in entries:
                try:
                    await self.handle_event(payload)
                    await self.consumer_group.ack(stream, self.group_name, msg_id)
                    total += 1
                    self.processed_count += 1
                except Exception as e:
                    logger.warning("Error processing event %s: %s", msg_id, e)
                    await self.consumer_group.ack(stream, self.group_name, msg_id)
        return total

    async def start(self) -> None:
        """Start the background consumer loop."""
        if self.running:
            return
        self.running = True
        await self.setup_groups()

        async def _loop() -> None:
            while self.running:
                try:
                    await self.process_once(count=10, block_ms=self.poll_interval_ms)
                except Exception as e:
                    logger.error("Error in campaign analytics worker loop: %s", e)
                await asyncio.sleep(self.poll_interval_ms / 1000.0)

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        """Stop background worker."""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
