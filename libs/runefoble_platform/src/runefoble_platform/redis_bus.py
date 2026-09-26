"""Redis Streams Event Bus implementation for distributed microservice communication."""

import logging
from typing import Any

from eventsource.adapters.serialization.json import json_dumps, json_loads
from eventsource.domain.event import DomainEvent
from eventsource.domain.event_registry import get_event_class_or_none
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

logger = logging.getLogger(__name__)


def deserialize_event(fields: dict[str, Any] | str) -> Any:
    """Deserialize Redis stream fields into a registered DomainEvent or dictionary.

    Recovers the registered DomainEvent class via
    eventsource.domain.event_registry.get_event_class_or_none(event_type).
    """
    if isinstance(fields, str):
        try:
            fields = json_loads(fields)
        except Exception:
            return fields

    if not isinstance(fields, dict):
        return fields

    event_dict: Any = fields
    event_type: str | None = fields.get("event_type")

    # If payload is encapsulated under "payload"
    if "payload" in fields:
        raw_payload = fields["payload"]
        if isinstance(raw_payload, str):
            try:
                parsed_payload = json_loads(raw_payload)
                if isinstance(parsed_payload, dict):
                    event_dict = parsed_payload
                else:
                    event_dict = {"data": parsed_payload}
            except Exception:
                event_dict = {"raw": raw_payload}
        elif isinstance(raw_payload, dict):
            event_dict = raw_payload

        if not event_type and isinstance(event_dict, dict):
            event_type = event_dict.get("event_type")

    if not event_type and isinstance(event_dict, dict):
        event_type = event_dict.get("event_type") or event_dict.get("type")

    if event_type and isinstance(event_dict, dict):
        event_cls = get_event_class_or_none(str(event_type))
        if event_cls is None and "." in str(event_type):
            short_type = str(event_type).split(".")[-1]
            event_cls = get_event_class_or_none(short_type)

        if event_cls is not None:
            try:
                return event_cls.model_validate(event_dict)
            except Exception as e:
                logger.warning(
                    "Found registered event class '%s' but validation failed: %s",
                    event_type,
                    e,
                )

    return event_dict


class RedisStreamsEventBus:
    """Distributed event bus powered by Redis Streams and Consumer Groups."""

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

    async def publish_event(self, stream: str, event: Any) -> str:
        """Publish a domain event, model, or dictionary to a Redis Stream via XADD."""
        client = await self.get_client()

        event_type: str = "GenericEvent"
        event_id: str | None = None
        payload: str

        if isinstance(event, DomainEvent):
            event_type = event.event_type or event.__class__.__name__
            event_id = str(event.event_id)
            payload = event.model_dump_json()
        elif isinstance(event, BaseModel):
            event_type = getattr(event, "event_type", event.__class__.__name__)
            raw_id = getattr(event, "event_id", None) or getattr(event, "id", None)
            event_id = str(raw_id) if raw_id is not None else None
            payload = event.model_dump_json()
        elif isinstance(event, dict):
            event_type = str(event.get("event_type") or event.get("type") or "GenericEvent")
            raw_id = event.get("event_id") or event.get("id")
            event_id = str(raw_id) if raw_id is not None else None
            payload = json_dumps(to_jsonable_python(event))
        else:
            event_type = getattr(event, "event_type", event.__class__.__name__)
            raw_id = getattr(event, "event_id", None) or getattr(event, "id", None)
            event_id = str(raw_id) if raw_id is not None else None
            try:
                payload = json_dumps(to_jsonable_python(event))
            except Exception:
                payload = json_dumps(event)

        entry_data: dict[str, str] = {
            "event_type": event_type,
            "payload": payload,
        }
        if event_id is not None:
            entry_data["event_id"] = event_id

        entry_id = await client.xadd(stream, entry_data)
        logger.debug(
            "Published event %s (%s) to %s as %s",
            event_id or "unspecified",
            event_type,
            stream,
            entry_id,
        )
        return entry_id

    async def create_consumer_group(self, stream: str, group_name: str) -> None:
        """Create a Redis consumer group if it does not already exist."""
        client = await self.get_client()
        try:
            await client.xgroup_create(stream, group_name, id="0", mkstream=True)
            logger.info("Created consumer group '%s' for stream '%s'", group_name, stream)
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group '%s' already exists for '%s'", group_name, stream)
            else:
                raise e

    async def read_group(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 2000,
        auto_deserialize: bool = False,
    ) -> list[tuple[str, Any]]:
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

        results: list[tuple[str, Any]] = []
        for _stream_name, messages in raw_entries:
            for msg_id, fields in messages:
                if auto_deserialize:
                    results.append((msg_id, deserialize_event(fields)))
                else:
                    try:
                        payload = json_loads(fields.get("payload", "{}"))
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


class MockAsyncRedis:
    """In-memory mock async Redis client simulating Redis Streams operations."""

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.groups: dict[tuple[str, str], int] = {}
        self.counter: int = 0
        self.closed: bool = False

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        self.counter += 1
        entry_id = f"1700000000000-{self.counter}"
        if stream not in self.streams:
            self.streams[stream] = []
        self.streams[stream].append((entry_id, fields))
        return entry_id

    async def xgroup_create(
        self, stream: str, group_name: str, id: str = "0", mkstream: bool = True
    ) -> bool:
        if stream not in self.streams and mkstream:
            self.streams[stream] = []
        key = (stream, group_name)
        if key in self.groups:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.groups[key] = 0
        return True

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 10,
        block: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, Any]]]]]:
        results: list[tuple[str, list[tuple[str, dict[str, Any]]]]] = []
        for stream_name, _start_id in streams.items():
            if stream_name not in self.streams:
                continue
            key = (stream_name, groupname)
            idx = self.groups.get(key, 0)
            available = self.streams[stream_name][idx : idx + count]
            self.groups[key] = idx + len(available)
            if available:
                results.append((stream_name, available))
        return results

    async def xack(self, stream: str, group_name: str, *message_ids: str) -> int:
        return len(message_ids)

    async def aclose(self) -> None:
        self.closed = True
