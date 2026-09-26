"""Distributed Redis Streams Consumer Groups and Dead Letter Queue (DLQ) support."""

from __future__ import annotations

import logging
import time
from typing import Any

from eventsource.adapters.serialization.json import json_dumps, json_loads
from eventsource.domain.event import DomainEvent
from eventsource.domain.event_registry import get_event_class_or_none
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from runefoble_platform.models import utc_now

logger = logging.getLogger(__name__)


def deserialize_event(fields: dict[str, Any] | str) -> Any:
    """Deserialize Redis stream fields into a registered DomainEvent or dictionary."""
    if isinstance(fields, str):
        try:
            fields = json_loads(fields)
        except Exception:
            return fields

    if not isinstance(fields, dict):
        return fields

    event_dict: Any = fields
    event_type: str | None = fields.get("event_type")

    if "payload" in fields:
        raw_payload = fields["payload"]
        if isinstance(raw_payload, str):
            try:
                parsed = json_loads(raw_payload)
                event_dict = parsed if isinstance(parsed, dict) else {"data": parsed}
            except Exception:
                event_dict = {"raw": raw_payload}
        elif isinstance(raw_payload, dict):
            event_dict = raw_payload

    if isinstance(event_dict, dict) and isinstance(fields, dict):
        if (
            "traceparent" in fields
            and "metadata" in event_dict
            and isinstance(event_dict["metadata"], dict)
            and "traceparent" not in event_dict["metadata"]
        ):
            event_dict["metadata"]["traceparent"] = fields["traceparent"]
        if (
            "tracestate" in fields
            and "metadata" in event_dict
            and isinstance(event_dict["metadata"], dict)
            and "tracestate" not in event_dict["metadata"]
        ):
            event_dict["metadata"]["tracestate"] = fields["tracestate"]

    if not event_type and isinstance(event_dict, dict):
        event_type = event_dict.get("event_type") or event_dict.get("type")

    if event_type and isinstance(event_dict, dict):
        event_cls = get_event_class_or_none(str(event_type))
        if event_cls is None and "." in str(event_type):
            event_cls = get_event_class_or_none(str(event_type).split(".")[-1])

        if event_cls is not None:
            try:
                event_obj = event_cls.model_validate(event_dict)
                if (
                    isinstance(fields, dict)
                    and "traceparent" in fields
                    and hasattr(event_obj, "metadata")
                    and isinstance(event_obj.metadata, dict)
                    and "traceparent" not in event_obj.metadata
                ):
                    event_obj.metadata["traceparent"] = fields["traceparent"]
                if (
                    isinstance(fields, dict)
                    and "tracestate" in fields
                    and hasattr(event_obj, "metadata")
                    and isinstance(event_obj.metadata, dict)
                    and "tracestate" not in event_obj.metadata
                ):
                    event_obj.metadata["tracestate"] = fields["tracestate"]
                return event_obj
            except Exception as e:
                logger.warning("Event validation failed for '%s': %s", event_type, e)
        else:
            if isinstance(fields, dict):
                if "traceparent" in fields and "traceparent" not in event_dict:
                    event_dict["traceparent"] = fields["traceparent"]
                if "tracestate" in fields and "tracestate" not in event_dict:
                    event_dict["tracestate"] = fields["tracestate"]

    return event_dict


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


class MockAsyncRedis:
    """In-memory mock async Redis client simulating Redis Streams operations and Consumer Groups."""

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.groups: dict[tuple[str, str], dict[str, Any]] = {}
        self.counter: int = 0
        self.closed: bool = False

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        self.counter += 1
        entry_id = f"1700000000000-{self.counter}"
        self.streams.setdefault(stream, []).append((entry_id, fields))
        return entry_id

    async def xgroup_create(
        self, stream: str, group_name: str, id: str = "0", mkstream: bool = True
    ) -> bool:
        if mkstream:
            self.streams.setdefault(stream, [])
        key = (stream, group_name)
        if key in self.groups:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.groups[key] = {"delivered_idx": 0, "pending": {}}
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
        for stream_name in streams:
            if stream_name not in self.streams or (stream_name, groupname) not in self.groups:
                continue
            group_data = self.groups[(stream_name, groupname)]
            idx = group_data["delivered_idx"]
            available = self.streams[stream_name][idx : idx + count]
            group_data["delivered_idx"] = idx + len(available)
            now = time.time()
            for msg_id, fields in available:
                group_data["pending"][msg_id] = {
                    "consumer": consumername,
                    "fields": fields,
                    "claimed_at": now,
                    "idle_time_ms": 0.0,
                }
            if available:
                results.append((stream_name, available))
        return results

    async def xack(self, stream: str, group_name: str, *message_ids: str) -> int:
        group_data = self.groups.get((stream, group_name))
        if not group_data:
            return 0
        return sum(1 for mid in message_ids if group_data["pending"].pop(mid, None) is not None)

    async def xautoclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        start_id: str = "0-0",
        count: int = 10,
        **_kwargs: Any,
    ) -> tuple[str, list[tuple[str, dict[str, Any]]], list[str]]:
        group_data = self.groups.get((name, groupname))
        if not group_data:
            return ("0-0", [], [])
        claimed: list[tuple[str, dict[str, Any]]] = []
        now = time.time()
        for mid, data in list(group_data["pending"].items()):
            idle_ms = data.get("idle_time_ms", 0.0) + (now - data.get("claimed_at", now)) * 1000.0
            if idle_ms >= min_idle_time:
                data.update({"consumer": consumername, "claimed_at": now, "idle_time_ms": 0.0})
                claimed.append((mid, data["fields"]))
                if len(claimed) >= count:
                    break
        return ("0-0", claimed, [])

    def set_message_idle(
        self, stream: str, group_name: str, message_id: str, idle_ms: float
    ) -> None:
        """Helper for unit tests: manually simulate idle elapsed time on a pending message."""
        key = (stream, group_name)
        if key in self.groups and message_id in self.groups[key]["pending"]:
            self.groups[key]["pending"][message_id]["idle_time_ms"] = idle_ms
            self.groups[key]["pending"][message_id]["claimed_at"] = time.time()

    def get_pending(self, stream: str, group_name: str) -> dict[str, dict[str, Any]]:
        """Helper for unit tests: query currently pending messages."""
        return dict(self.groups.get((stream, group_name), {}).get("pending", {}))

    async def aclose(self) -> None:
        self.closed = True


__all__ = ["deserialize_event", "RedisConsumerGroup", "MockAsyncRedis"]
