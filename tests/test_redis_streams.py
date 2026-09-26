"""Tests for Redis Streams Event Bus infrastructure."""

import datetime
import uuid
from typing import Any

import pytest
from pydantic import BaseModel
from runefoble_events.events import SessionCreated, TokenMoved
from runefoble_platform.redis_bus import RedisStreamsEventBus, deserialize_event


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


class SampleModel(BaseModel):
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
    assert fields["event_type"] == "SessionCreated"
    assert str(event.event_id) == fields["event_id"]
    assert "Test Campaign Kickoff" in fields["payload"]


@pytest.mark.asyncio
async def test_publish_pydantic_model(
    event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    model = SampleModel(name="Aragorn", score=100)
    entry_id = await event_bus.publish_event("runefoble.events.test", model)
    assert entry_id == "1700000000000-1"

    _, fields = mock_redis.streams["runefoble.events.test"][0]
    assert fields["event_type"] == "SampleModel"
    assert "Aragorn" in fields["payload"]


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


@pytest.mark.asyncio
async def test_create_consumer_group(event_bus: RedisStreamsEventBus) -> None:
    # First creation should succeed
    await event_bus.create_consumer_group("runefoble.events.board", "board_workers")

    # Second creation should gracefully catch BUSYGROUP
    await event_bus.create_consumer_group("runefoble.events.board", "board_workers")


@pytest.mark.asyncio
async def test_read_group_and_acknowledge(
    event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    stream = "runefoble.events.board"
    group = "board_group"
    consumer = "worker_1"

    await event_bus.create_consumer_group(stream, group)

    event = TokenMoved(
        aggregate_id=uuid.uuid4(),
        token_id="token-42",
        name="Goblin Scout",
        from_x=0,
        from_y=0,
        to_x=3,
        to_y=5,
    )
    await event_bus.publish_event(stream, event)

    # Read messages without auto_deserialize
    messages = await event_bus.read_group(stream, group, consumer, count=5)
    assert len(messages) == 1
    msg_id, payload = messages[0]
    assert isinstance(payload, dict)
    assert payload["token_id"] == "token-42"
    assert payload["to_x"] == 3

    # Acknowledge message
    acked = await event_bus.acknowledge(stream, group, msg_id)
    assert acked == 1

    # Empty read after consumption
    empty = await event_bus.read_group(stream, group, consumer, count=5)
    assert empty == []


@pytest.mark.asyncio
async def test_read_group_auto_deserialize(event_bus: RedisStreamsEventBus) -> None:
    stream = "runefoble.events.session"
    group = "session_group"
    consumer = "worker_2"

    await event_bus.create_consumer_group(stream, group)

    session_id = uuid.uuid4()
    event = SessionCreated(
        aggregate_id=session_id,
        title="Epic Quest",
    )
    await event_bus.publish_event(stream, event)

    # Read with auto_deserialize=True
    messages = await event_bus.read_group(stream, group, consumer, count=5, auto_deserialize=True)
    assert len(messages) == 1
    _msg_id, deserialized = messages[0]
    assert isinstance(deserialized, SessionCreated)
    assert deserialized.aggregate_id == session_id
    assert deserialized.title == "Epic Quest"


def test_deserialize_event_helper() -> None:
    session_id = uuid.uuid4()
    event = SessionCreated(aggregate_id=session_id, title="Registered Event")

    # 1. From Redis stream fields dict with payload JSON string
    fields = {
        "event_type": "SessionCreated",
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

    # 3. From CloudEvents namespaced type
    ce_fields = {
        "event_type": "runefoble.SessionCreated",
        "payload": event.model_dump_json(),
    }
    deserialized_ce = deserialize_event(ce_fields)
    assert isinstance(deserialized_ce, SessionCreated)

    # 4. Unregistered event type returns dictionary
    unregistered_fields = {
        "event_type": "NonExistentEvent",
        "payload": '{"key": "value"}',
    }
    assert deserialize_event(unregistered_fields) == {"key": "value"}

    # 5. Non-dict input
    assert deserialize_event(42) == 42  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_close(event_bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis) -> None:
    assert not mock_redis.closed
    await event_bus.close()
    assert mock_redis.closed
    assert event_bus._client is None
