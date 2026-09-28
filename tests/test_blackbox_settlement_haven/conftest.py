"""Shared fixtures and assertion helpers for settlement haven blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0010, and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus() -> Generator[MockAsyncRedis]:
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> Generator[MockSpiceDBClient]:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app)


def assert_event_emitted(mock_bus: MockAsyncRedis, event_name: str) -> None:
    """Verify that an event matching the given name was published to Redis streams."""
    entries = mock_bus.streams.get("runefoble.events.west_marches", [])
    ev_norm = event_name.lower().replace("_", "")
    assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
        f"Expected event '{event_name}' in stream, but found: {entries}"
    )
