"""Distributed Redis Streams Consumer Groups and Dead Letter Queue (DLQ) support."""

from __future__ import annotations

import logging
from typing import Any

from eventsource.adapters.serialization.json import json_dumps
from eventsource.domain.event import DomainEvent
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from runefoble_platform.event_deserializer import deserialize_event
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.models import utc_now

logger = logging.getLogger(__name__)


class RedisConsumerGroup:
    """Manages Redis Streams consumer groups, competing worker consumption, ACK, auto-claiming, and DLQ."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        client: Any | None = None,
    ) -> None:
        self.redis_url = redis_url
        self._client: Any | None = client

    async def get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def create_group(
        self,
        stream: str,
        group_name: str,
        start_id: str = "0",
        make_stream: bool = True,
    ) -> bool:
        """Create consumer group. Idempotent: returns False if BUSYGROUP, True if created."""
        client = await self.get_client()
        try:
            await client.xgroup_create(stream, group_name, id=start_id, mkstream=make_stream)
            logger.info("Created consumer group '%s' for stream '%s'", group_name, stream)
            return True
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group '%s' already exists for '%s'", group_name, stream)
                return False
            raise e

    async def read_group(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 2000,
    ) -> list[tuple[str, Any]]:
        """Read pending or new messages for a consumer group using XREADGROUP and deserialize."""
        client = await self.get_client()
        raw_entries = await client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )
        if not raw_entries:
            return []

        results: list[tuple[str, Any]] = []
        for _stream_name, messages in raw_entries:
            for msg_id, fields in messages:
                results.append((str(msg_id), deserialize_event(fields)))
        return results

    async def ack(
        self,
        stream: str,
        group_name: str,
        message_ids: list[str] | str,
    ) -> int:
        """Acknowledge processed messages with XACK."""
        client = await self.get_client()
        ids = [message_ids] if isinstance(message_ids, str) else list(message_ids)
        return await client.xack(stream, group_name, *ids) if ids else 0

    async def auto_claim_pending(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
        min_idle_ms: int = 60000,
        count: int = 10,
    ) -> list[tuple[str, Any]]:
        """Reclaim pending/unacknowledged messages with XAUTOCLAIM."""
        client = await self.get_client()
        raw_res = await client.xautoclaim(
            name=stream,
            groupname=group_name,
            consumername=consumer_name,
            min_idle_time=min_idle_ms,
            start_id="0-0",
            count=count,
        )
        if not raw_res:
            return []

        messages = (
            raw_res[1] if isinstance(raw_res, (list, tuple)) and len(raw_res) >= 2 else raw_res
        )
        results: list[tuple[str, Any]] = []
        for item in messages:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                results.append((str(item[0]), deserialize_event(item[1])))
        return results

    async def route_to_dead_letter(
        self,
        stream: str,
        message_id: str,
        payload: dict[str, Any] | Any,
        error_reason: str,
        max_retries: int = 3,
    ) -> str:
        """Route poison/failed message to {stream}.dlq with failure metadata."""
        client = await self.get_client()
        dlq_stream = f"{stream}.dlq"

        if isinstance(payload, (DomainEvent, BaseModel)):
            payload_str = payload.model_dump_json()
        elif isinstance(payload, (dict, list)):
            payload_str = json_dumps(to_jsonable_python(payload))
        else:
            payload_str = str(payload)

        dlq_entry = {
            "original_stream": stream,
            "original_message_id": str(message_id),
            "payload": payload_str,
            "error_reason": error_reason,
            "max_retries": str(max_retries),
            "failed_at": utc_now().isoformat(),
            "event_type": "DeadLetterEvent",
        }
        entry_id = await client.xadd(dlq_stream, dlq_entry)
        logger.warning("Routed %s from %s to %s: %s", message_id, stream, dlq_stream, error_reason)
        return str(entry_id)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


RedisConsumerGroupWorker = RedisConsumerGroup

__all__ = [
    "deserialize_event",
    "RedisConsumerGroup",
    "RedisConsumerGroupWorker",
    "MockAsyncRedis",
]
