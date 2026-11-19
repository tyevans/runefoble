"""Blackbox tests for the one event-type reader (TASK-0821).

Every publish and consume path reads the event type through `event_type_of`. An event
without a type is an error. No path substitutes a placeholder name such as "GenericEvent".

The Redis client is a process-boundary double. The publish and consume calls are the
public bus and handler frontdoors.
"""

from __future__ import annotations

import random
import uuid
from typing import Any

import pytest
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_events.events import SessionCreated
from runefoble_platform.dice import roll_d20, roll_die
from runefoble_platform.event_fields import EventTypeMissingError, event_field, event_type_of
from runefoble_platform.event_publish import publish_best_effort, publish_or_fail
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.sync_verifier import sync_test_verifier


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=mock_redis)


class _TypelessEvent:
    """An object that carries no event type."""


def test_domain_event_publishes_its_wire_name(
    bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    event = SessionCreated(aggregate_id=uuid.uuid4(), title="Typed")

    assert event_type_of(event) == "runefoble.events.session.created"
    assert event_type_of(event) == event.event_type


@pytest.mark.asyncio
async def test_untyped_dict_publish_fails_and_writes_nothing(
    bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    with pytest.raises(EventTypeMissingError):
        await bus.publish_event("runefoble.events.untyped", {"title": "no type"})

    assert "runefoble.events.untyped" not in mock_redis.streams


@pytest.mark.asyncio
async def test_untyped_object_publish_fails_and_writes_nothing(
    bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    with pytest.raises(EventTypeMissingError):
        await bus.publish_event("runefoble.events.untyped", _TypelessEvent())

    assert "runefoble.events.untyped" not in mock_redis.streams


@pytest.mark.asyncio
async def test_typed_dict_publishes_under_its_type(
    bus: RedisStreamsEventBus, mock_redis: MockAsyncRedis
) -> None:
    await bus.publish_event("runefoble.events.custom", {"type": "org.runefoble.Custom", "a": 1})

    _, fields = mock_redis.streams["runefoble.events.custom"][0]
    assert fields["event_type"] == "org.runefoble.Custom"


@pytest.mark.asyncio
async def test_publish_or_fail_rejects_untyped_event_before_publishing(
    mock_redis: MockAsyncRedis, bus: RedisStreamsEventBus
) -> None:
    with pytest.raises(EventTypeMissingError):
        await publish_or_fail(bus, "runefoble.events.untyped", {"title": "no type"})

    assert "runefoble.events.untyped" not in mock_redis.streams


@pytest.mark.asyncio
async def test_publish_best_effort_rejects_untyped_event(
    mock_redis: MockAsyncRedis, bus: RedisStreamsEventBus
) -> None:
    with pytest.raises(EventTypeMissingError):
        await publish_best_effort(bus, "runefoble.events.untyped", {"title": "no type"})

    assert "runefoble.events.untyped" not in mock_redis.streams


def test_cloudevent_dict_reads_type_from_data() -> None:
    cloud_event = {"specversion": "1.0", "data": {"event_type": "org.runefoble.Nested"}}

    assert event_type_of(cloud_event) == "org.runefoble.Nested"


def test_event_field_reads_top_level_then_data_then_default() -> None:
    payload: dict[str, Any] = {"campaign_id": "c-1", "data": {"session_id": "s-1"}}

    assert event_field(payload, "campaign_id") == "c-1"
    assert event_field(payload, "session_id") == "s-1"
    assert event_field(payload, "missing", "fallback") == "fallback"


def test_event_field_treats_none_as_absent() -> None:
    payload: dict[str, Any] = {"campaign_id": None}

    assert event_field(payload, "campaign_id", "default") == "default"


@pytest.mark.asyncio
async def test_untyped_payload_is_rejected_by_zanzibar_sync() -> None:
    service = ZitadelSpiceDBSyncService(MockSpiceDBClient(), sync_test_verifier())

    with pytest.raises(EventTypeMissingError):
        await service.handle_domain_event({"campaign_id": str(uuid.uuid4())})


def test_roll_d20_returns_explicit_roll_without_rolling() -> None:
    assert roll_d20(explicit=17) == 17


def test_roll_d20_uses_the_supplied_generator() -> None:
    assert roll_d20(rng=random.Random(42)) == random.Random(42).randint(1, 20)


def test_roll_die_stays_within_the_faces() -> None:
    rng = random.Random(7)
    rolls = [roll_die(6, rng) for _ in range(200)]

    assert min(rolls) >= 1
    assert max(rolls) <= 6
