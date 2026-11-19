"""Real-Redis blackbox test for stream reclaim (TASK-0854).

A consumer reads a message and dies before it acknowledges. A live consumer on a real Redis
server reclaims the message with XAUTOCLAIM and runs its handler once. The test uses a Redis
container, so it needs Docker and is marked `docker`. Run it with:
uv run pytest -m docker tests/test_blackbox_stream_consumers_real_redis.py

Governed by ADR-0006 (Redis Streams transport) and Hard Invariant 7.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from runefoble_events.events import SessionCreated
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import ReclaimPolicy, StreamConsumer

from tests.helpers.ports import free_port
from tests.helpers.redis_container import redis_container

pytestmark = pytest.mark.docker


@pytest.fixture
def real_redis_url() -> Iterator[str]:
    with redis_container(free_port()) as url:
        yield url


def test_reclaim_takes_over_a_pending_message_from_a_dead_consumer_on_real_redis(
    real_redis_url: str,
) -> None:
    stream = f"runefoble.events.session.reclaim-{uuid4().hex[:8]}"
    group = "reclaim_real_group"

    async def scenario() -> tuple[list[str], int, dict[str, Any]]:
        consumer_group = RedisConsumerGroup(redis_url=real_redis_url)
        try:
            client = await consumer_group.get_client()
            await consumer_group.create_group(stream, group, start_id="0")
            await RedisStreamsEventBus(client=client).publish_event(
                stream,
                SessionCreated(
                    aggregate_id=uuid4(), session_id=str(uuid4()), campaign_id=str(uuid4())
                ),
            )
            dead_reads = await consumer_group.read_group(stream, group, "worker_dead")
            assert len(dead_reads) == 1
            dead_msg_id = dead_reads[0][0]

            handled: list[str] = []

            async def handler(message_id: str, _event: Any) -> None:
                handled.append(message_id)

            live = StreamConsumer(
                consumer_group,
                stream,
                group,
                "worker_live",
                handler,
                reclaim=ReclaimPolicy(min_idle_ms=10, every_polls=1),
            )
            await asyncio.sleep(0.05)
            assert await live.poll_once(block_ms=1) == 1
            assert await live.poll_once(block_ms=1) == 0
            pending = await client.xpending(stream, group)
            return [dead_msg_id, *handled], live.processed_count, pending
        finally:
            await consumer_group.close()

    ids, processed, pending = asyncio.run(scenario())

    assert ids[0] == ids[1]
    assert len(ids) == 2
    assert processed == 1
    assert pending["pending"] == 0
