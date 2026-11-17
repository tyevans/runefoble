"""Blackbox TDD frontdoor test suite for Autonomous NPC Faction Radar UI Microfrontend.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization (Redacts private DM intelligence)
- ADR-0006: Redis Streams Event Bus (Real-time world tick event updates)
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
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
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.dependencies import (
    get_spicedb_client,
    set_campaign_world_repo,
    set_event_bus,
    set_faction_repo,
    set_spicedb_client,
)
from the_watcher.factions import FactionAggregate
from the_watcher.factions.campaign_world import CampaignWorldAggregate
from the_watcher.main import app

from tests.helpers.mock_redis import MockAsyncRedis

@pytest.fixture(autouse=True)
def clean_simulation_environment():
    """Ensure clean SpiceDB, simulation engine, event store, and bus before and after each test."""
    set_spicedb_client(MockSpiceDBClient())
    set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))
    test_store = InMemoryEventStore()
    test_bus = InMemoryEventBus()
    repo = AggregateRepository(
        event_store=test_store,
        aggregate_factory=FactionAggregate,
        event_publisher=test_bus,
    )
    set_faction_repo(repo)
    set_campaign_world_repo(
        AggregateRepository(
            event_store=test_store,
            aggregate_factory=CampaignWorldAggregate,
            event_publisher=test_bus,
        )
    )
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)
    set_faction_repo(None)
    set_campaign_world_repo(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


async def _setup_campaign_roles(
    dm_user: str = "dm_evelyn", player_user: str = "player_valeros"
) -> tuple[str, str, str]:
    """Helper to seed SpiceDB Zanzibar roles on a campaign."""
    camp_id = f"camp-{uuid4().hex[:8]}"
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="player",
        subject_type="user",
        subject_id=player_user,
    )
    return camp_id, dm_user, player_user


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_the_watcher_ui_manifest_advertises_faction_radar(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes runefoble-faction-radar component."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "the_watcher"
    assert data["package"] == "@runefoble/the-watcher-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-faction-radar" in data["components"]
    assert "runefoble-autonomous-dm" in data["components"]
    assert "runefoble-watcher-feed" in data["components"]


# ---------------------------------------------------------------------------
# 2. REST Frontdoor Data Binding & Zanzibar Redaction Integration (ADR-0001)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rest_frontdoor_zanzibar_redaction_and_data_binding(client: TestClient) -> None:
    """Verify ADR-0001 object-level authorization: private DM briefing is redacted for players."""
    camp_id, dm_user, player_user = await _setup_campaign_roles()

    # 1. DM executes world progression tick
    tick_res = client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 55, "random_seed": 42},
        headers={"X-User-Id": dm_user},
    )
    assert tick_res.status_code == 200
    tick_data = tick_res.json()
    assert tick_data["tick_number"] == 1
    assert len(tick_data["factions"]) >= 3
    assert len(tick_data["tavern_rumors"]) > 0
    assert "THE WATCHER INTELLIGENCE BULLETIN" in tick_data["intelligence_bulletin"]

    # 2. DM fetches latest bulletin -> receives full unredacted intelligence briefing
    dm_bulletin_res = client.get(
        f"/api/v1/campaigns/{camp_id}/world-ticks/latest",
        headers={"X-User-Id": dm_user},
    )
    assert dm_bulletin_res.status_code == 200
    dm_bulletin = dm_bulletin_res.json()
    assert dm_bulletin["tick_number"] == 1
    assert "THE WATCHER INTELLIGENCE BULLETIN" in dm_bulletin["intelligence_bulletin"]
    assert len(dm_bulletin["factions"]) >= 3
    assert len(dm_bulletin["tavern_rumors"]) > 0

    # 3. Player fetches latest bulletin -> intelligence_bulletin is REDACTED per ADR-0001
    player_bulletin_res = client.get(
        f"/api/v1/campaigns/{camp_id}/world-ticks/latest",
        headers={"X-User-Id": player_user},
    )
    assert player_bulletin_res.status_code == 200
    player_bulletin = player_bulletin_res.json()
    assert player_bulletin["tick_number"] == 1
    # Intelligence bulletin is empty/redacted for player
    assert player_bulletin["intelligence_bulletin"] == ""
    # But public rumors and faction states are visible to player
    assert len(player_bulletin["factions"]) >= 3
    assert len(player_bulletin["tavern_rumors"]) > 0

    # 4. Unauthorized outsider gets 403 Forbidden
    outsider_res = client.get(
        f"/api/v1/campaigns/{camp_id}/world-ticks/latest",
        headers={"X-User-Id": "unauthorized_stranger"},
    )
    assert outsider_res.status_code == 403

    # 5. Player queries public faction list for radar data binding
    factions_res = client.get(
        f"/api/v1/campaigns/{camp_id}/factions",
        headers={"X-User-Id": player_user},
    )
    assert factions_res.status_code == 200
    factions = factions_res.json()
    assert len(factions) >= 3
    for f in factions:
        assert "name" in f
        assert "influence" in f
        assert "resources" in f
        assert "disposition" in f
        assert "active_goal" in f
        assert "goal_progress" in f
        assert "goal_target" in f
        assert "territory" in f
