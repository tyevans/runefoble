"""Shared test harness and fixtures for Faction Turf War blackbox tests.

Governed by ADR-0002, ADR-0003, ADR-0006, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    InMemoryEventBus,
    InMemoryEventStore,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.dependencies import (
    get_spicedb_client,
    set_event_bus,
    set_regional_unrest_repo,
    set_spicedb_client,
)
from the_watcher.main import app
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture(autouse=True)
def clean_turf_war_environment(mock_redis: MockAsyncRedis):
    """Configure mock SpiceDB, event store, mock redis bus, and unrest repo before each test."""
    set_spicedb_client(MockSpiceDBClient())
    set_event_bus(RedisStreamsEventBus(client=mock_redis))
    set_regional_unrest_repo(
        AggregateRepository(
            event_store=InMemoryEventStore(),
            aggregate_factory=RegionalUnrestAggregate,
            event_publisher=InMemoryEventBus(),
        )
    )
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)
    set_regional_unrest_repo(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


async def setup_campaign_roles(
    dm_user: str = "dm_evelyn", player_user: str = "player_valeros"
) -> tuple[str, str, str]:
    """Helper to seed SpiceDB Zanzibar roles on a campaign."""
    camp_id = str(uuid4())
    spicedb = get_spicedb_client()
    for rel, user in [("dungeon_master", dm_user), ("player", player_user)]:
        await spicedb.write_relationship("campaign", camp_id, rel, "user", user)
    return camp_id, dm_user, player_user
