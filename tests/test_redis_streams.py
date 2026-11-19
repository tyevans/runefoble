"""Tests for Redis Streams Event Bus infrastructure."""

import datetime
import json
import uuid
from typing import Any

import pytest
from pydantic import BaseModel
from runefoble_events.events import SessionCreated
from runefoble_platform.event_deserializer import EventDecodeError, UnknownEvent, deserialize_event
from runefoble_platform.event_fields import EventTypeMissingError
from runefoble_platform.redis_bus import RedisStreamsEventBus


class MockAsyncRedis:
    """In-memory mock async Redis client simulating Redis Streams operations."""

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.counter: int = 0
        self.closed: bool = False

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        self.counter += 1
        entry_id = f"1700000000000-{self.counter}"
        if stream not in self.streams:
            self.streams[stream] = []
        self.streams[stream].append((entry_id, fields))
        return entry_id

    async def aclose(self) -> None:
        self.closed = True


class SampleModel(BaseModel):
    name: str
    score: int


class TypedSampleModel(BaseModel):
    event_type: str = "runefoble.events.test.sample"
    name: str
    score: int


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=mock_redis)


@pytest.mark.asyncio
async def test_publish_domain_event(
    event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    session_id = uuid.uuid4()
    event = SessionCreated(
        aggregate_id=session_id,
        title="Test Campaign Kickoff",
    )

    entry_id = await event_bus.publish_event("runefoble.events.session", event)
    assert entry_id == "1700000000000-1"
    assert "runefoble.events.session" in mock_redis.streams

    stored_id, fields = mock_redis.streams["runefoble.events.session"][0]
    assert stored_id == entry_id
    assert fields["event_type"] == "runefoble.events.session.created"
    assert str(event.event_id) == fields["event_id"]
    assert "Test Campaign Kickoff" in fields["payload"]


@pytest.mark.asyncio
async def test_publish_typed_pydantic_model_uses_its_event_type(
    event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    model = TypedSampleModel(name="Aragorn", score=100)
    entry_id = await event_bus.publish_event("runefoble.events.test", model)
    assert entry_id == "1700000000000-1"

    _, fields = mock_redis.streams["runefoble.events.test"][0]
    assert fields["event_type"] == "runefoble.events.test.sample"
    assert "Aragorn" in fields["payload"]


@pytest.mark.asyncio
async def test_publish_untyped_pydantic_model_fails_loudly(
    event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    with pytest.raises(EventTypeMissingError):
        await event_bus.publish_event("runefoble.events.test", SampleModel(name="x", score=1))

    assert "runefoble.events.test" not in mock_redis.streams


@pytest.mark.asyncio
async def test_publish_dict_with_uuid_and_datetime(
    event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    event_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.UTC)
    data = {
        "event_id": event_id,
        "event_type": "CustomLogEvent",
        "timestamp": now,
        "metadata": {"campaign": "Underdark", "levels": [1, 2, 3]},
    }

    entry_id = await event_bus.publish_event("runefoble.events.logs", data)
    assert entry_id == "1700000000000-1"

    _, fields = mock_redis.streams["runefoble.events.logs"][0]
    assert fields["event_type"] == "CustomLogEvent"
    assert fields["event_id"] == str(event_id)
    assert "Underdark" in fields["payload"]


def test_deserialize_event_helper() -> None:
    session_id = uuid.uuid4()
    event = SessionCreated(aggregate_id=session_id, title="Registered Event")

    # 1. From Redis stream fields dict with payload JSON string
    fields = {
        "event_type": "runefoble.events.session.created",
        "payload": event.model_dump_json(),
    }
    deserialized = deserialize_event(fields)
    assert isinstance(deserialized, SessionCreated)
    assert deserialized.aggregate_id == session_id
    assert deserialized.title == "Registered Event"

    # 2. From already unpacked dictionary
    unpacked = event.model_dump(mode="json")
    deserialized_unpacked = deserialize_event(unpacked)
    assert isinstance(deserialized_unpacked, SessionCreated)
    assert deserialized_unpacked.aggregate_id == session_id

    # 3. A retired class-name identifier does not resolve to an event
    retired_fields = {
        "event_type": "runefoble.SessionCreated",
        "payload": event.model_dump_json(),
    }
    assert not isinstance(deserialize_event(retired_fields), SessionCreated)

    # 4. Unregistered event type returns an explicit UnknownEvent
    unregistered_fields = {
        "event_type": "NonExistentEvent",
        "payload": '{"key": "value"}',
    }
    unknown = deserialize_event(unregistered_fields)
    assert isinstance(unknown, UnknownEvent)
    assert unknown.event_type == "NonExistentEvent"
    assert unknown.fields == {"key": "value"}


def test_deserialize_event_rejects_undecodable_input() -> None:
    # A non-JSON string is not an event.
    with pytest.raises(EventDecodeError):
        deserialize_event("not json")

    # A JSON value that is not an object is not an event.
    with pytest.raises(EventDecodeError):
        deserialize_event(42)  # type: ignore[arg-type]

    # A payload that is not JSON is not an event.
    with pytest.raises(EventDecodeError):
        deserialize_event({"event_type": "NonExistentEvent", "payload": "{broken"})

    # Fields without an event type cannot be routed.
    with pytest.raises(EventDecodeError):
        deserialize_event({"payload": '{"key": "value"}'})


def test_deserialize_event_rejects_registered_event_that_fails_validation() -> None:
    event = SessionCreated(aggregate_id=uuid.uuid4(), title="Missing Field")
    payload = event.model_dump(mode="json")
    del payload["aggregate_id"]
    fields = {
        "event_type": "runefoble.events.session.created",
        "payload": json.dumps(payload),
    }

    with pytest.raises(EventDecodeError):
        deserialize_event(fields)


@pytest.mark.asyncio
async def test_close(event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis) -> None:
    assert not mock_redis.closed
    await event_bus.close()
    assert mock_redis.closed
    assert event_bus._client is None
