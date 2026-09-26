"""Redis Streams Event Bus implementation for distributed microservice communication."""

import json
import logging
from typing import Any

from runefoble_events.events import BaseRunefobleEvent

logger = logging.getLogger(__name__)


class RedisStreamsEventBus:
    """Distributed event bus powered by Redis Streams and Consumer Groups."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._client: Any | None = None

    async def get_client(self) -> Any:
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._client

    async def publish_event(self, stream: str, event: BaseRunefobleEvent) -> str:
        """Publish a CloudEvents-compliant domain event to a Redis Stream via XADD."""
        client = await self.get_client()
        payload = event.model_dump_json()
        entry_id = await client.xadd(stream, {"event_type": event.event_type, "payload": payload})
        logger.debug(f"Published event {event.id} ({event.event_type}) to {stream} as {entry_id}")
        return entry_id

    async def create_consumer_group(self, stream: str, group_name: str) -> None:
        """Create a Redis consumer group if it does not already exist."""
        client = await self.get_client()
        try:
            await client.xgroup_create(stream, group_name, id="0", mkstream=True)
            logger.info(f"Created consumer group '{group_name}' for stream '{stream}'")
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group '{group_name}' already exists for '{stream}'")
            else:
                raise e

    async def read_group(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 2000,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Read pending or new messages for a consumer group using XREADGROUP."""
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

        results: list[tuple[str, dict[str, Any]]] = []
        for _stream_name, messages in raw_entries:
            for msg_id, fields in messages:
                try:
                    payload = json.loads(fields.get("payload", "{}"))
                    results.append((msg_id, payload))
                except Exception:
                    results.append((msg_id, fields))
        return results

    async def acknowledge(self, stream: str, group_name: str, message_id: str) -> int:
        """Acknowledge processed message with XACK."""
        client = await self.get_client()
        return await client.xack(stream, group_name, message_id)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
