"""Blackbox TDD tests for West Marches modular aggregate and handlers (TASK-0205).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- ADR-0011: PostgreSQL Multi-Database Persistent Event Store
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 2: Domain state transitions via eventsource-py DeclarativeAggregate
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from campaign_lore.dependencies import set_spicedb_client, set_west_marches_repo
from campaign_lore.main import app as lore_app
from campaign_lore.models import WestMarchesState
from campaign_lore.west_marches_aggregate import (
    FACILITY_BOONS,
    WestMarchesAtlasAggregate,
    WestMarchesWorldAggregate,
    calculate_boons,
)
from campaign_lore.west_marches_handlers import (
    calculate_defensive_buffer,
    evaluate_territory_claim,
)
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.event_sourcing import create_aggregate_repository

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)
    yield mock_db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient) -> TestClient:
    fresh_repo = create_aggregate_repository(WestMarchesAtlasAggregate)
    set_west_marches_repo(fresh_repo)
    return TestClient(lore_app)


def test_hard_invariant_6_file_length_limits() -> None:
    """Verify decomposed aggregate and handlers strictly adhere to line count limits."""
    agg_path = (
        REPO_ROOT
        / "services"
        / "campaign_lore"
        / "src"
        / "campaign_lore"
        / "west_marches_aggregate.py"
    )
    handlers_path = (
        REPO_ROOT
        / "services"
        / "campaign_lore"
        / "src"
        / "campaign_lore"
        / "west_marches_handlers.py"
    )
    models_path = REPO_ROOT / "services" / "campaign_lore" / "src" / "campaign_lore" / "models.py"

    agg_lines = len(agg_path.read_text(encoding="utf-8").splitlines())
    handlers_lines = len(handlers_path.read_text(encoding="utf-8").splitlines())
    models_lines = len(models_path.read_text(encoding="utf-8").splitlines())

    assert agg_lines < 150, (
        f"west_marches_aggregate.py has {agg_lines} lines (limit: strictly < 150)"
    )
    assert handlers_lines < 130, (
        f"west_marches_handlers.py has {handlers_lines} lines (limit: strictly < 130)"
    )
    assert models_lines < 500, f"models.py has {models_lines} lines (limit: < 500)"


def test_backward_compatibility_exports() -> None:
    """Verify that public interfaces and alias mappings remain fully backward compatible."""
    assert WestMarchesWorldAggregate is WestMarchesAtlasAggregate
    assert issubclass(WestMarchesAtlasAggregate, object)
    assert hasattr(WestMarchesAtlasAggregate, "handle_created")
    assert hasattr(WestMarchesAtlasAggregate, "handle_campaign_registered")
    assert hasattr(WestMarchesAtlasAggregate, "handle_discovery_shared")
    assert hasattr(WestMarchesAtlasAggregate, "handle_outpost_established")
    assert hasattr(WestMarchesAtlasAggregate, "handle_outpost_upgraded")
    assert hasattr(WestMarchesAtlasAggregate, "handle_notice_posted")

    state = WestMarchesState()
    assert state.world_name == "The Frontier Marches"
    assert "watchtower" in FACILITY_BOONS


def test_territory_claim_evaluation() -> None:
    """Verify territory claim distance conflict evaluation logic extracted to handlers."""
    existing_outposts = {
        "outpost_alpha": {
            "name": "Alpha Fort",
            "coordinates": {"x": 100.0, "y": 100.0},
        },
        "outpost_beta": {
            "name": "Beta Station",
            "coordinates": {"x": 200.0, "y": 200.0},
        },
    }

    # Claim far away from any outpost (no conflict)
    assert evaluate_territory_claim({"x": 150.0, "y": 150.0}, existing_outposts, min_dist=10.0)

    # Claim too close to Alpha Fort (within 5.0 units when min_dist=10.0 -> conflict)
    assert not evaluate_territory_claim({"x": 103.0, "y": 104.0}, existing_outposts, min_dist=10.0)

    # Claim with empty existing outposts
    assert evaluate_territory_claim({"x": 10.0, "y": 10.0}, {}, min_dist=10.0)


def test_outpost_facility_boons_and_defense_calculations() -> None:
    """Verify boons and defensive buffer calculations extracted to handlers."""
    facs = {"watchtower": 2, "trading_post": 1, "alchemical_workshop": 1}
    boons = calculate_boons(facs)
    assert "Early Warning (+1 Initiative)" in boons
    assert "Scouting Advantage (No Ambush)" in boons
    assert "Market Access" in boons
    assert "Reagent Extraction (+1 Herbal Reagent)" in boons

    buffer_rating = calculate_defensive_buffer(facs, level=2)
    # watchtower (2 * 10) + level (2 * 5) = 20 + 10 = 30
    assert buffer_rating == 30


@pytest.mark.asyncio
async def test_frontdoor_record_discovery_pin(
    client: TestClient, spicedb_client: MockSpiceDBClient
) -> None:
    """Frontdoor verification: record discovery pin via HTTP route."""
    cid = uuid4()
    uid = "ranger_john"
    await spicedb_client.write_relationship("campaign", str(cid), "player", "user", uid)

    payload = {
        "name": "Sunken Temple of Eldath",
        "discovery_type": "dungeon",
        "coordinates": {"x": 150.0, "y": 220.0},
        "discovered_by_party_name": "The Wayfarers",
        "description": "Ancient overgrown ruins beneath the marsh canopy.",
        "danger_level": 3,
        "metadata": {"relic_rumor": "Chalice of Spring"},
    }

    resp = client.post(
        f"/api/v1/campaigns/{cid}/west-marches/discoveries",
        json=payload,
        headers={"x-user-id": uid},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "created"
    assert data["discovery"]["name"] == "Sunken Temple of Eldath"
    assert data["discovery"]["danger_level"] == 3
    assert data["discovery"]["discovered_by_party_name"] == "The Wayfarers"

    # Query atlas to ensure discovery appears in aggregate projection
    atlas_resp = client.get(
        f"/api/v1/campaigns/{cid}/west-marches",
        headers={"x-user-id": uid},
    )
    assert atlas_resp.status_code == 200
    atlas_data = atlas_resp.json()
    assert len(atlas_data["discoveries"]) >= 1
    found = next(
        (d for d in atlas_data["discoveries"] if d["name"] == "Sunken Temple of Eldath"),
        None,
    )
    assert found is not None
    assert found["coordinates"] == {"x": 150.0, "y": 220.0}


@pytest.mark.asyncio
async def test_frontdoor_upgrade_outpost_facility(
    client: TestClient, spicedb_client: MockSpiceDBClient
) -> None:
    """Frontdoor verification: upgrade communal outpost facility and recalculate boons."""
    cid = uuid4()
    uid = "smith_helen"
    await spicedb_client.write_relationship("campaign", str(cid), "player", "user", uid)

    # First upgrade watchtower to tier 2
    upgrade_payload = {
        "facility_id": "watchtower",
        "gold_spent": 150,
        "materials_spent": {"timber": 30, "stone": 20},
    }

    resp = client.post(
        f"/api/v1/campaigns/{cid}/west-marches/stronghold/upgrade",
        json=upgrade_payload,
        headers={"x-user-id": uid},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "upgraded"
    assert data["facility_id"] == "watchtower"
    assert data["new_tier"] == 2
    assert "Scouting Advantage (No Ambush)" in data["active_boons"]
    assert data["defensive_buffer"] >= 25  # tier 2 watchtower (20) + level 1 (5)


@pytest.mark.asyncio
async def test_frontdoor_post_tavern_notice(
    client: TestClient, spicedb_client: MockSpiceDBClient
) -> None:
    """Frontdoor verification: post bounty notice to communal tavern board."""
    cid = uuid4()
    uid = "innkeeper_toby"
    await spicedb_client.write_relationship("campaign", str(cid), "player", "user", uid)

    notice_payload = {
        "author_name": "Toby the Barkeep",
        "title": "Bounty: Marsh Ghouls",
        "content": "Clear the undead lurking near the old causeway.",
        "notice_type": "bounty",
        "bounty_reward": 200,
    }

    resp = client.post(
        f"/api/v1/campaigns/{cid}/west-marches/tavern-board/notices",
        json=notice_payload,
        headers={"x-user-id": uid},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "posted"
    assert data["notice"]["title"] == "Bounty: Marsh Ghouls"
    assert data["notice"]["bounty_reward"] == 200

    # Verify board state
    atlas_resp = client.get(
        f"/api/v1/campaigns/{cid}/west-marches",
        headers={"x-user-id": uid},
    )
    assert atlas_resp.status_code == 200
    board = atlas_resp.json()["tavern_board"]
    assert any(n["title"] == "Bounty: Marsh Ghouls" for n in board)
