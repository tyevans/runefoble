"""Tests for Redis Streams Consumer Groups, pending entries, and DLQ routing."""

from uuid import uuid4

import pytest
from runefoble_events.events import (
    SessionCreated,
    TokenMoved,
)
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def consumer_group(mock_redis: MockAsyncRedis) -> RedisConsumerGroup:
    return RedisConsumerGroup(client=mock_redis)


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=mock_redis)


@pytest.mark.asyncio
async def test_group_creation_idempotent(consumer_group: RedisConsumerGroup) -> None:
    stream = "runefoble.events.test"
    group = "test_workers"

    # First creation succeeds and returns True
    created = await consumer_group.create_group(stream, group)
    assert created is True

    # Second creation catches BUSYGROUP and returns False without raising
    recreated = await consumer_group.create_group(stream, group)
    assert recreated is False


@pytest.mark.asyncio
async def test_competing_consumers_divide_messages(
    consumer_group: RedisConsumerGroup,
    event_bus: RedisStreamsEventBus,
) -> None:
    stream = "runefoble.events.board"
    group = "board_group"

    await consumer_group.create_group(stream, group)

    # Publish 4 token move events
    for i in range(4):
        event = TokenMoved(
            aggregate_id=uuid4(),
            token_id=f"token-{i}",
            name=f"Hero-{i}",
            from_x=i,
            from_y=i,
            to_x=i + 1,
            to_y=i + 1,
        )
        await event_bus.publish_event(stream, event)

    # Consumer A reads 2 messages
    msgs_a = await consumer_group.read_group(stream, group, "consumer_a", count=2)
    assert len(msgs_a) == 2
    ids_a = [msg_id for msg_id, _ in msgs_a]
    tokens_a = [event.token_id for _, event in msgs_a]
    assert tokens_a == ["token-0", "token-1"]

    # Competing Consumer B reads next 2 messages
    msgs_b = await consumer_group.read_group(stream, group, "consumer_b", count=2)
    assert len(msgs_b) == 2
    ids_b = [msg_id for msg_id, _ in msgs_b]
    tokens_b = [event.token_id for _, event in msgs_b]
    assert tokens_b == ["token-2", "token-3"]

    # Verify complete division and zero partition overlap
    assert set(ids_a).isdisjoint(set(ids_b))


@pytest.mark.asyncio
async def test_ack_acknowledgment_and_pending_removal(
    consumer_group: RedisConsumerGroup,
    mock_redis: MockAsyncRedis,
    event_bus: RedisStreamsEventBus,
) -> None:
    stream = "runefoble.events.session"
    group = "session_group"

    await consumer_group.create_group(stream, group)

    # Publish 2 events
    for i in range(2):
        event = SessionCreated(aggregate_id=uuid4(), title=f"Chapter {i}")
        await event_bus.publish_event(stream, event)

    # Read messages
    messages = await consumer_group.read_group(stream, group, "worker_1", count=2)
    assert len(messages) == 2
    msg1_id, _ = messages[0]
    msg2_id, _ = messages[1]

    # Verify both are currently in pending list
    pending = mock_redis.get_pending(stream, group)
    assert len(pending) == 2
    assert msg1_id in pending
    assert msg2_id in pending

    # ACK single message id (string)
    acked = await consumer_group.ack(stream, group, msg1_id)
    assert acked == 1

    pending_after_first = mock_redis.get_pending(stream, group)
    assert len(pending_after_first) == 1
    assert msg1_id not in pending_after_first
    assert msg2_id in pending_after_first

    # ACK list of message ids
    acked_second = await consumer_group.ack(stream, group, [msg2_id])
    assert acked_second == 1

    # Pending list should now be clean
    assert len(mock_redis.get_pending(stream, group)) == 0


@pytest.mark.asyncio
async def test_auto_claim_pending_stalled_consumer(
    consumer_group: RedisConsumerGroup,
    mock_redis: MockAsyncRedis,
    event_bus: RedisStreamsEventBus,
) -> None:
    stream = "runefoble.events.tasks"
    group = "tasks_group"

    await consumer_group.create_group(stream, group)

    event = TokenMoved(
        aggregate_id=uuid4(),
        token_id="stalled_token",
        name="Scout",
        from_x=0,
        from_y=0,
        to_x=5,
        to_y=5,
    )
    msg_id = await event_bus.publish_event(stream, event)

    # Worker A reads message but stalls without ACKing
    messages = await consumer_group.read_group(stream, group, "worker_stalled", count=1)
    assert len(messages) == 1
    assert messages[0][0] == msg_id

    # Check pending ownership belongs to worker_stalled
    pending = mock_redis.get_pending(stream, group)
    assert pending[msg_id]["consumer"] == "worker_stalled"

    # Simulate 65 seconds idle time passing
    mock_redis.set_message_idle(stream, group, msg_id, idle_ms=65000)

    # Worker B claims messages idle for more than 60,000ms
    claimed = await consumer_group.auto_claim_pending(
        stream,
        group,
        consumer_name="worker_reclaimer",
        min_idle_ms=60000,
        count=10,
    )

    assert len(claimed) == 1
    claimed_id, claimed_event = claimed[0]
    assert claimed_id == msg_id
    assert isinstance(claimed_event, TokenMoved)
    assert claimed_event.token_id == "stalled_token"

    # Pending consumer ownership transferred to worker_reclaimer
    updated_pending = mock_redis.get_pending(stream, group)
    assert updated_pending[msg_id]["consumer"] == "worker_reclaimer"

    # Worker B completes and ACKs
    acked = await consumer_group.ack(stream, group, claimed_id)
    assert acked == 1
    assert len(mock_redis.get_pending(stream, group)) == 0


@pytest.mark.asyncio
async def test_dead_letter_queue_routing(
    consumer_group: RedisConsumerGroup,
    mock_redis: MockAsyncRedis,
) -> None:
    stream = "runefoble.events.orders"
    poison_msg_id = "1700000000000-99"
    corrupt_payload = {"malformed": "data", "missing_fields": True}
    reason = "ValidationError: Missing required field aggregate_id"

    dlq_id = await consumer_group.route_to_dead_letter(
        stream=stream,
        message_id=poison_msg_id,
        payload=corrupt_payload,
        error_reason=reason,
        max_retries=3,
    )

    assert dlq_id is not None
    dlq_stream = "runefoble.events.orders.dlq"
    assert dlq_stream in mock_redis.streams
    assert len(mock_redis.streams[dlq_stream]) == 1

    stored_id, entry_fields = mock_redis.streams[dlq_stream][0]
    assert stored_id == dlq_id
    assert entry_fields["original_stream"] == stream
    assert entry_fields["original_message_id"] == poison_msg_id
    assert entry_fields["error_reason"] == reason
    assert entry_fields["max_retries"] == "3"
    assert entry_fields["event_type"] == "DeadLetterEvent"
    assert "malformed" in entry_fields["payload"]
