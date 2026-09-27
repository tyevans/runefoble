"""Shared test harness and fixtures for Faction Resources and Bribery blackbox tests.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
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
    set_faction_resource_repo,
    set_spicedb_client,
)
from the_watcher.factions.resources.aggregate import FactionResourceAggregate
from the_watcher.main import app


@pytest.fixture(autouse=True)
def clean_resource_environment():
    """Configure mock SpiceDB, event store, bus, and repo before each test."""
    set_spicedb_client(MockSpiceDBClient())
    set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))
    test_store = InMemoryEventStore()
    test_bus = InMemoryEventBus()
    repo = AggregateRepository(
        event_store=test_store,
        aggregate_factory=FactionResourceAggregate,
        event_publisher=test_bus,
    )
    set_faction_resource_repo(repo)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)
    set_faction_resource_repo(None)


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
        await spicedb.write_relationship(
            resource_type="campaign",
            resource_id=camp_id,
            relation=rel,
            subject_type="user",
            subject_id=user,
        )
    return camp_id, dm_user, player_user
