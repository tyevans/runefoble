"""Shared fixtures and harness for caravan contracts blackbox tests.

Governed by: ADR-0001, ADR-0006, ADR-0011, Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    set_event_bus,
    set_spicedb_client,
)
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus() -> Generator[MockAsyncRedis]:
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> Generator[MockSpiceDBClient]:
    mock = MockSpiceDBClient()
    set_spicedb_client(mock)
    yield mock
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(session_app)


def assert_stream_events(mock_bus: MockAsyncRedis, *event_names: str) -> None:
    """Verify published CloudEvents on the West Marches Redis stream."""
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    for event in event_names:
        assert any(event in str(entry[1]) for entry in entries)
