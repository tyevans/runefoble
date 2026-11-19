"""Redis Streams Event Bus implementation for distributed microservice communication."""

from __future__ import annotations

import logging
from typing import Any

from eventsource.adapters.serialization.json import json_dumps
from eventsource.domain.event import DomainEvent
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from runefoble_platform.event_fields import event_type_of
from runefoble_platform.telemetry import inject_trace_context

logger = logging.getLogger(__name__)


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

        event_id: str | None = None
        payload: str

        carrier = inject_trace_context()
        traceparent = carrier.get("traceparent")
        tracestate = carrier.get("tracestate")

        if isinstance(event, DomainEvent):
            if traceparent and "traceparent" not in event.metadata:
                event.metadata["traceparent"] = traceparent
            if tracestate and "tracestate" not in event.metadata:
                event.metadata["tracestate"] = tracestate
            event_type = event_type_of(event)
            event_id = str(event.event_id)
            payload = event.model_dump_json()
        elif isinstance(event, BaseModel):
            event_type = event_type_of(event)
            raw_id = getattr(event, "event_id", None) or getattr(event, "id", None)
            event_id = str(raw_id) if raw_id is not None else None
            payload = event.model_dump_json()
        elif isinstance(event, dict):
            event_type = event_type_of(event)
            raw_id = event.get("event_id") or event.get("id")
            event_id = str(raw_id) if raw_id is not None else None
            if traceparent and "traceparent" not in event:
                event["traceparent"] = traceparent
            if tracestate and "tracestate" not in event:
                event["tracestate"] = tracestate
            if traceparent and "metadata" in event and isinstance(event["metadata"], dict):
                event["metadata"].setdefault("traceparent", traceparent)
            payload = json_dumps(to_jsonable_python(event))
        else:
            event_type = event_type_of(event)
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
        if traceparent:
            entry_data["traceparent"] = traceparent
        if tracestate:
            entry_data["tracestate"] = tracestate

        entry_id = await client.xadd(stream, entry_data)

        logger.debug(
            "Published event %s (%s) to %s as %s",
            event_id or "unspecified",
            event_type,
            stream,
            entry_id,
        )
        return entry_id

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


__all__ = ["RedisStreamsEventBus"]
