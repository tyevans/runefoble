"""Blackbox tests for fatal ambush caravan destruction and UI microfrontend manifest.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
- ADR-0013: Microfrontend Architecture & Component Manifest
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import create_campaign, join_campaign

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.mark.asyncio
async def test_blackbox_caravan_destroyed_and_ui_manifest(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
):
    """Test Scenario 4: Catastrophic caravan destruction and UI microfrontend registration."""
    officer_id = "officer_dane"
    contractor_id = "ranger_thorn"

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Perilous Range"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    world_id = world_res.json()["shared_world_id"]

    campaign_id = create_campaign(client, officer_id)
    join_campaign(client, campaign_id, officer_id, contractor_id)

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_id, "party_name": "Ranger Corps"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )

    # Post, accept, and dispatch
    post_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "HighlandKeep",
            "destination_outpost": "Shadowfen",
            "cargo": {"potions": 10},
            "cargo_value": 500,
            "route_risk_level": "medium",
            "transit_stages": 2,
            "reward_gold": 250,
            "posted_by_campaign_id": campaign_id,
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    cid = post_res.json()["contract"]["contract_id"]

    accept_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/accept",
        json={"contractor_campaign_id": campaign_id, "contractor_party_name": "Ranger Corps"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(contractor_id)}"},
    )
    assert accept_res.status_code == 200, accept_res.text
    dispatch_setup = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/dispatch",
        json={},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(contractor_id)}"},
    )
    assert dispatch_setup.status_code == 200, dispatch_setup.text

    # Report catastrophic ambush: caravan destroyed
    ambush_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/ambush",
        json={
            "stage_index": 1,
            "ambush_type": "red_dragon",
            "danger_level": 5,
            "outcome": "caravan_destroyed",
            "cargo_loss_percentage": 1.0,
            "notes": "Red dragon incinerated the entire caravan.",
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(contractor_id)}"},
    )
    assert ambush_res.status_code == 200
    assert ambush_res.json()["status"] == "failed"

    # Attempting to fulfill a destroyed contract must fail
    fail_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/fulfill",
        json={},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(contractor_id)}"},
    )
    assert fail_res.status_code == 400

    # Verify UI microfrontend manifest advertises runefoble-caravan-board
    ui_manifest_res = client.get("/ui/manifest")
    assert ui_manifest_res.status_code == 200
    manifest = ui_manifest_res.json()
    assert "runefoble-caravan-board" in manifest["components"]
