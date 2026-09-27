"""Shared fixtures and harness for reaction interrupts and ready-action test suite."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    bus_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=bus_client)
    set_event_bus(bus)
    watcher_set_event_bus(bus)
    yield bus_client
    set_event_bus(None)
    watcher_set_event_bus(None)


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(mock_bus: MockAsyncRedis, spicedb_client: MockSpiceDBClient) -> TestClient:
    return TestClient(session_app)


@pytest.fixture
def watcher_client(mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(watcher_app)
