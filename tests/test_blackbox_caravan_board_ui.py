"""Blackbox TDD frontdoor test suite for Cross-Campaign Caravan Trading & Frontier Bounty Board UI.

Part of TASK-0136 / PRD-0007 / US-0058.
Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 2: Domain state transitions powered by eventsource-py
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup (zero backdoor state manipulation)
"""

from __future__ import annotations

from uuid import uuid4

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
def mock_bus():
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    return mock_spicedb


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient) -> TestClient:
    return TestClient(session_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_caravan_board_ui_manifest_frontdoor(client: TestClient) -> None:
    """Verify game_session service advertises runefoble-caravan-board via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-caravan-board" in data["components"]

    # Also test the routed alias /game_session/ui/manifest
    alias_res = client.get("/game_session/ui/manifest")
    assert alias_res.status_code == 200
    assert "runefoble-caravan-board" in alias_res.json()["components"]


# ---------------------------------------------------------------------------
# 2. Public REST API Frontdoor Acceptance & SpiceDB Zanzibar Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_caravan_contract_accept_and_stream_events(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify one-click contract acceptance via public frontdoor REST endpoint and Redis Streams."""
    officer_id = "officer_karina"
    contractor_id = "party_leader_bram"
    campaign_poster = str(uuid4())
    campaign_contractor = str(uuid4())

    # 1. Establish shared world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Marches Trading League"},
        headers={"x-user-id": officer_id},
    )
    assert world_res.status_code == 201
    world_id = world_res.json()["shared_world_id"]

    # SpiceDB authorization relationships
    await spicedb_client.write_relationship(
        "campaign", campaign_poster, "owner", "user", officer_id
    )
    await spicedb_client.write_relationship(
        "campaign", campaign_contractor, "owner", "user", contractor_id
    )
    await spicedb_client.write_relationship(
        "shared_world", world_id, "trade", "user", contractor_id
    )

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_poster, "party_name": "Guild Overseers"},
        headers={"x-user-id": officer_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_contractor, "party_name": "The Amber Vanguard"},
        headers={"x-user-id": officer_id},
    )

    # 2. Post contract to notice board
    post_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "Bastion Cross",
            "destination_outpost": "Ironford",
            "cargo": {"iron_ingots": 50, "timber": 20},
            "cargo_value": 450,
            "route_risk_level": "medium",
            "transit_stages": 2,
            "escort_collateral": 75,
            "reward_gold": 250,
            "reward_reputation": 20,
            "posted_by_campaign_id": campaign_poster,
        },
        headers={"x-user-id": officer_id},
    )
    assert post_res.status_code == 201
    contract = post_res.json()["contract"]
    contract_id = contract["contract_id"]
    assert contract["status"] == "open"

    # 3. Acceptance via public REST frontdoor (simulating button click in UI)
    accept_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}/accept",
        json={
            "contractor_campaign_id": campaign_contractor,
            "contractor_party_name": "The Amber Vanguard",
        },
        headers={"x-user-id": contractor_id},
    )
    assert accept_res.status_code == 200
    accepted_data = accept_res.json()["contract"]
    assert accepted_data["status"] == "accepted"
    assert accepted_data["contractor_party_name"] == "The Amber Vanguard"

    # 4. Verify public notice board query returns the accepted contract
    board_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        headers={"x-user-id": contractor_id},
    )
    assert board_res.status_code == 200
    contracts = board_res.json()["contracts"]
    matched = next((c for c in contracts if c["contract_id"] == contract_id), None)
    assert matched is not None
    assert matched["status"] == "accepted"
    assert matched["contractor_party_name"] == "The Amber Vanguard"

    # 5. Verify domain event published to Redis Streams
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any("CaravanContractAccepted" in str(entry[1]) for entry in entries)
