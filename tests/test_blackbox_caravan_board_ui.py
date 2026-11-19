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

import pytest
from fastapi.testclient import TestClient
from game_session.shared.streams import STREAM_WEST_MARCHES
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.game_session_app import session_app
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


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


# ---------------------------------------------------------------------------
# 2. Public REST API Frontdoor Acceptance & SpiceDB Zanzibar Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_caravan_contract_accept_and_stream_events(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify one-click contract acceptance via public frontdoor REST endpoint and Redis Streams."""
    officer_id = "officer_karina"
    contractor_id = "party_leader_bram"
    # 1. Establish shared world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Marches Trading League"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    assert world_res.status_code == 201
    world_id = world_res.json()["shared_world_id"]

    # Registration needs guild officer and campaign owner, so the officer owns both campaigns.
    # The contractor plays in the contractor campaign, which grants trade on the world.
    campaign_poster = create_campaign(client, officer_id)
    campaign_contractor = create_campaign(client, officer_id)
    invite_and_join(client, campaign_contractor, officer_id, contractor_id)

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_poster, "party_name": "Guild Overseers"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_contractor, "party_name": "The Amber Vanguard"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(contractor_id)}"},
    )
    assert accept_res.status_code == 200
    accepted_data = accept_res.json()["contract"]
    assert accepted_data["status"] == "accepted"
    assert accepted_data["contractor_party_name"] == "The Amber Vanguard"

    # 4. Verify public notice board query returns the accepted contract
    board_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(contractor_id)}"},
    )
    assert board_res.status_code == 200
    contracts = board_res.json()["contracts"]
    matched = next((c for c in contracts if c["contract_id"] == contract_id), None)
    assert matched is not None
    assert matched["status"] == "accepted"
    assert matched["contractor_party_name"] == "The Amber Vanguard"

    # 5. Verify domain event published to Redis Streams
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any(
        "runefoble.events.west_marches.caravan_contract_accepted" in str(entry[1])
        for entry in entries
    )
