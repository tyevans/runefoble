"""Shared fixtures and harness for West Marches blackbox test suite.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app as session_app
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
def spicedb_client() -> MockSpiceDBClient:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient) -> TestClient:
    return TestClient(session_app)


@pytest.fixture
def party_ids() -> dict[str, str]:
    return {
        "officer": "rowan_officer",
        "blue_player": "blue_explorer",
        "gold_player": "gold_scout",
        "campaign_blue": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
        "campaign_gold": "d2b3c4d5-e6f7-8a9b-0c1d-2e3f4a5b6c7d",
    }
