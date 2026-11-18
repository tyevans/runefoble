"""Blackbox tests for durable world tick state (TASK-0569).

Governed by:
- ADR-0011: eventsource-py Core Event Sourcing
- ADR-0006: Redis Streams Event Bus
- Hard Invariant 2: Domain state changes flow through DeclarativeAggregate subclasses
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

A restart is simulated by discarding every process-level object (simulation engine,
aggregate repositories, event bus) and rebuilding them over the same durable event store
and the same Redis double. Tests interact only through public HTTP routes and the stream.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from eventsource.adapters.memory.bus import InMemoryEventBus
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    InMemoryEventStore,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.dependencies import (
    set_campaign_world_repo,
    set_event_bus,
    set_faction_repo,
    set_faction_simulation_engine,
)
from the_watcher.factions import FactionAggregate
from the_watcher.factions.campaign_world import CampaignWorldAggregate
from the_watcher.main import app
from the_watcher.simulation_engine import FactionSimulationEngine

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

WATCHER_STREAM = "runefoble.events.watcher"
WORLD_TICK_TYPE = "runefoble.events.watcher.world_tick_executed"


pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _boot(store: InMemoryEventStore, redis: MockAsyncRedis) -> None:
    """Start a fresh process: new engine and repositories over the durable store."""
    set_faction_repo(
        AggregateRepository(
            event_store=store,
            aggregate_factory=FactionAggregate,
            event_publisher=InMemoryEventBus(),
        )
    )
    set_campaign_world_repo(
        AggregateRepository(
            event_store=store,
            aggregate_factory=CampaignWorldAggregate,
            event_publisher=InMemoryEventBus(),
        )
    )
    set_faction_simulation_engine(FactionSimulationEngine())
    set_event_bus(RedisStreamsEventBus(client=redis))


@pytest.fixture(autouse=True)
def durable_environment():
    yield
    set_event_bus(None)
    set_faction_repo(None)
    set_campaign_world_repo(None)
    set_faction_simulation_engine(FactionSimulationEngine())


@pytest.mark.asyncio
async def test_tick_count_registry_and_latest_bulletin_survive_restart(trusted_ws_issuer):
    """After a restart the tick resumes at 3, the registry keeps one faction, and no defaults return."""
    store = InMemoryEventStore()
    redis = MockAsyncRedis()
    _boot(store, redis)
    client = TestClient(app)

    camp_id = str(uuid4())
    dm_user = "dm_restart"
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"}

    created = client.post(
        f"/api/v1/campaigns/{camp_id}/factions",
        json={
            "name": "Ironfang Syndicate",
            "influence": 65,
            "active_goal": "Smuggle Arcane Weapons into Oakhaven",
            "territory": "Oakhaven Docks",
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    faction_id = created.json()["faction_id"]

    last_tick = None
    for seed in (1, 2):
        last_tick = client.post(
            f"/api/v1/campaigns/{camp_id}/world-tick",
            json={"regional_stability": 50, "random_seed": seed},
            headers=headers,
        )
        assert last_tick.status_code == 200, last_tick.text
    assert last_tick is not None
    assert last_tick.json()["tick_number"] == 2
    bulletin_before_restart = last_tick.json()["intelligence_bulletin"]

    _boot(store, redis)
    client = TestClient(app)

    resumed = client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 50, "random_seed": 3},
        headers=headers,
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["tick_number"] == 3
    assert [f["faction_id"] for f in resumed.json()["factions"]] == [faction_id]

    listed = client.get(f"/api/v1/campaigns/{camp_id}/factions", headers=headers)
    assert listed.status_code == 200
    assert [f["faction_id"] for f in listed.json()] == [faction_id]

    faction = client.get(f"/api/v1/campaigns/{camp_id}/factions/{faction_id}", headers=headers)
    assert faction.status_code == 200
    assert len(faction.json()["history"]) == 3

    latest = client.get(f"/api/v1/campaigns/{camp_id}/world-ticks/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json()["tick_number"] == 3
    assert bulletin_before_restart != latest.json()["intelligence_bulletin"]
    assert "WORLD TICK #3" in latest.json()["intelligence_bulletin"]


@pytest.mark.asyncio
async def test_each_world_tick_writes_one_stream_entry_in_order(trusted_ws_issuer):
    """Three ticks, spread across a restart, write three world_tick_executed entries in order."""
    store = InMemoryEventStore()
    redis = MockAsyncRedis()
    _boot(store, redis)
    client = TestClient(app)

    camp_id = str(uuid4())
    dm_user = "dm_stream"
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"}

    client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 50, "random_seed": 1},
        headers=headers,
    )
    client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 50, "random_seed": 2},
        headers=headers,
    )

    _boot(store, redis)
    client = TestClient(app)
    res = client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 50, "random_seed": 3},
        headers=headers,
    )
    assert res.status_code == 200, res.text

    entries = [
        json.loads(fields["payload"])
        for _entry_id, fields in redis.streams.get(WATCHER_STREAM, [])
        if fields.get("event_type") == WORLD_TICK_TYPE
    ]
    assert [e["tick_number"] for e in entries] == [1, 2, 3]
    assert all(e["campaign_id"] == camp_id for e in entries)
