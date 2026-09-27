"""Shared test harness and fixtures for blackbox settlement tests.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(app)


def assert_stream_events(mock_bus: MockAsyncRedis, *event_names: str) -> None:
    """Assert domain event was published to mock Redis stream."""
    entries = mock_bus.streams.get("runefoble.events.west_marches", [])
    for event in event_names:
        ev_norm = event.lower().replace("_", "")
        assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
            f"Expected event '{event}' in West Marches stream, but found: {entries}"
        )
