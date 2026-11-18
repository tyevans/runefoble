"""Supervised Redis Streams consumers.

A consumer reads one stream for one consumer group. It acknowledges a message only after its
handler succeeds. A handler failure routes the message to the dead-letter stream and then
acknowledges it. Start-up failures raise, so the owning service fails to start. Runtime failures
are logged and reported through ``status``, which services publish on ``/healthz``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any

from runefoble_platform.consumer_group import RedisConsumerGroup

logger = logging.getLogger("runefoble.platform.stream_consumer")

EventHandler = Callable[[str, Any], Awaitable[None]]
"""Handler for one stream message. It receives the stream message id and the decoded payload."""

ResumePosition = Callable[[], Awaitable[str | None]]
"""Return the stream id to resume from, or None to keep the group position."""

RUNNING = "running"
FAILED = "failed"

_MAX_BACKOFF_S = 5.0


class StreamConsumer:
    """Reads one stream for one consumer group and acknowledges handled messages."""

    def __init__(
        self,
        consumer_group: RedisConsumerGroup,
        stream: str,
        group_name: str,
        consumer_name: str,
        handler: EventHandler,
        poll_interval_s: float = 0.1,
        resume_position: ResumePosition | None = None,
    ) -> None:
        self.consumer_group = consumer_group
        self.stream = stream
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.handler = handler
        self.poll_interval_s = poll_interval_s
        self.resume_position = resume_position
        self.processed_count = 0
        self.dead_letter_count = 0
        self.last_error: str | None = None
        self._task: asyncio.Task[None] | None = None

    async def ensure_group(self) -> None:
        """Create the consumer group, then move it to the resume position when one is known.

        Errors other than BUSYGROUP propagate.
        """
        await self.consumer_group.create_group(
            stream=self.stream,
            group_name=self.group_name,
            start_id="0",
            make_stream=True,
        )
        if self.resume_position is None:
            return
        position = await self.resume_position()
        if position is not None:
            await self.consumer_group.set_group_position(self.stream, self.group_name, position)

    async def poll_once(self, count: int = 10, block_ms: int = 100) -> int:
        """Read one batch, run the handler on each message, and acknowledge the results."""
        entries = await self.consumer_group.read_group(
            stream=self.stream,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
        )
        handled = 0
        for msg_id, payload in entries:
            try:
                await self.handler(msg_id, payload)
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                logger.error("Handler failed for %s on %s: %s", msg_id, self.stream, reason)
                await self.consumer_group.route_to_dead_letter(self.stream, msg_id, payload, reason)
                await self.consumer_group.ack(self.stream, self.group_name, msg_id)
                self.dead_letter_count += 1
            else:
                await self.consumer_group.ack(self.stream, self.group_name, msg_id)
                self.processed_count += 1
            handled += 1
        return handled

    def start(self) -> None:
        """Start the background read loop on the running event loop."""
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name=f"consumer:{self.stream}")

    async def _run(self) -> None:
        backoff_s = self.poll_interval_s
        while True:
            try:
                handled = await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                logger.error("Consumer on %s failed to read: %s", self.stream, self.last_error)
                await asyncio.sleep(backoff_s)
                backoff_s = min(backoff_s * 2, _MAX_BACKOFF_S)
                continue
            self.last_error = None
            backoff_s = self.poll_interval_s
            if handled == 0:
                await asyncio.sleep(self.poll_interval_s)

    async def stop(self) -> None:
        """Cancel the read loop and wait for it to finish."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    @property
    def status(self) -> str:
        """Return ``running`` while the loop lives and the last read succeeded."""
        if self._task is None or self._task.done() or self.last_error is not None:
            return FAILED
        return RUNNING


class SupervisedStreamConsumers:
    """A named set of stream consumers that starts, stops, and reports as one unit."""

    def __init__(self, name: str, consumers: Iterable[StreamConsumer]) -> None:
        self.name = name
        self.consumers: list[StreamConsumer] = list(consumers)

    async def start(self) -> None:
        """Create every consumer group first, then start the read loops.

        Raises when any group cannot be created, so the owning service fails to start.
        """
        for consumer in self.consumers:
            await consumer.ensure_group()
        for consumer in self.consumers:
            consumer.start()
        logger.info("Started consumers '%s' on %d stream(s)", self.name, len(self.consumers))

    async def ensure_groups(self) -> None:
        for consumer in self.consumers:
            await consumer.ensure_group()

    async def poll_once(self, count: int = 10, block_ms: int = 100) -> int:
        total = 0
        for consumer in self.consumers:
            total += await consumer.poll_once(count=count, block_ms=block_ms)
        return total

    async def stop(self) -> None:
        for consumer in self.consumers:
            await consumer.stop()

    @property
    def processed_count(self) -> int:
        return sum(consumer.processed_count for consumer in self.consumers)

    @property
    def status(self) -> str:
        """Return ``running`` only when every consumer in the set is running."""
        if all(consumer.status == RUNNING for consumer in self.consumers):
            return RUNNING
        return FAILED


def consumer_statuses(consumers: Mapping[str, SupervisedStreamConsumers]) -> dict[str, str]:
    """Map consumer set names to status values for a ``/healthz`` response."""
    return {name: consumer_set.status for name, consumer_set in consumers.items()}


__all__ = [
    "FAILED",
    "RUNNING",
    "EventHandler",
    "StreamConsumer",
    "SupervisedStreamConsumers",
    "consumer_statuses",
]
