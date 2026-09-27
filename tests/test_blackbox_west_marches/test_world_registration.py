"""Blackbox tests for West Marches world creation and campaign registration.

Governed by ADR-0001, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_establish_persistent_frontier_world(client: TestClient):
    """Guild officer creates a persistent West Marches shared frontier world."""
    officer_id = "rowan_officer"
    res = client.post(
        "/api/v1/shared-worlds",
        json={
            "name": "The Sunken Marches",
            "frontier_region": "The Shadowed Fenlands",
            "description": "A vast, dangerous marshland explored by mercenary guilds.",
        },
        headers={"x-user-id": officer_id},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    world_id = data["shared_world_id"]
    assert data["name"] == "The Sunken Marches"
    assert data["frontier_region"] == "The Shadowed Fenlands"

    query_res = client.get(
        f"/api/v1/shared-worlds/{world_id}",
        headers={"x-user-id": officer_id},
    )
    assert query_res.status_code == 200
    assert query_res.json()["shared_world_id"] == world_id


@pytest.mark.asyncio
async def test_link_campaigns_to_shared_world(client: TestClient, party_ids: dict[str, str]):
    """Multiple adventuring parties link their campaigns to the shared frontier."""
    officer = party_ids["officer"]
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Basin", "frontier_region": "Sunken Delta"},
        headers={"x-user-id": officer},
    )
    world_id = world_res.json()["shared_world_id"]

    for camp_key, party_name in [
        ("campaign_blue", "Party Blue"),
        ("campaign_gold", "Party Gold"),
    ]:
        res = client.post(
            f"/api/v1/shared-worlds/{world_id}/campaigns",
            json={"campaign_id": party_ids[camp_key], "party_name": party_name},
            headers={"x-user-id": officer},
        )
        assert res.status_code == 201
        assert res.json()["party_name"] == party_name
        assert res.json()["status"] == "registered"

    world_data = client.get(
        f"/api/v1/shared-worlds/{world_id}",
        headers={"x-user-id": officer},
    ).json()
    assert party_ids["campaign_blue"] in world_data["registered_campaigns"]
    assert party_ids["campaign_gold"] in world_data["registered_campaigns"]


@pytest.mark.asyncio
async def test_duplicate_registration_and_validation(client: TestClient):
    """Verify duplicate campaign registration handling and UUID validation."""
    officer_id = "rowan_officer"
    camp_id = str(uuid4())

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Mistveil Reach"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    res1 = client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": camp_id, "party_name": "The Rangers"},
        headers={"x-user-id": officer_id},
    )
    assert res1.status_code == 201

    res2 = client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": camp_id, "party_name": "The Veteran Rangers"},
        headers={"x-user-id": officer_id},
    )
    assert res2.status_code == 201
    assert res2.json()["party_name"] == "The Veteran Rangers"

    inv_res = client.get("/api/v1/shared-worlds/invalid-uuid", headers={"x-user-id": officer_id})
    assert inv_res.status_code == 400
