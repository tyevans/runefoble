"""Blackbox test suite for West Marches atlas pins, discovery logs, and Zanzibar access.

Part of TASK-0176 / PRD-0018 / US-0050.
Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 6: File length limit (< 500 lines, target < 120 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient


@pytest.mark.asyncio
async def test_blackbox_west_marches_overview_and_zanzibar_access(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify GET /api/v1/campaigns/{id}/west-marches enforces SpiceDB Zanzibar permissions."""
    campaign_id = str(uuid4())
    player_id = "rowan_ranger"
    outsider_id = "unauthorized_wanderer"

    # 1. Unauthorized outsider is rejected (HTTP 403)
    unauth_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": outsider_id},
    )
    assert unauth_resp.status_code == 403

    # 2. Grant player view permission in SpiceDB Zanzibar
    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 3. Authorized player receives communal frontier state
    auth_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": player_id},
    )
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert data["campaign_id"] == campaign_id
    assert "outposts" in data
    assert len(data["outposts"]) >= 1


@pytest.mark.asyncio
async def test_blackbox_discovery_pins_and_popover_data(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
    sample_discovery_payload: dict[str, Any],
) -> None:
    """Verify placing milestone discovery pins and retrieving popover metadata."""
    campaign_id = str(uuid4())
    player_id = "blue_explorer"

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_id,
    )

    # 1. Record milestone discovery: "Sunken Crypt of Arnor"
    disc_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/discoveries",
        json=sample_discovery_payload,
        headers={"x-user-id": player_id},
    )
    assert disc_resp.status_code == 201
    disc_data = disc_resp.json()["discovery"]
    assert disc_data["name"] == "Sunken Crypt of Arnor"
    assert disc_data["danger_level"] == 4
    assert disc_data["discovered_by_party_name"] == "Party Blue"

    # 2. Query overview and verify pin appears in discoveries list
    overview = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches",
        headers={"x-user-id": player_id},
    ).json()
    assert len(overview["discoveries"]) == 1
    assert overview["discoveries"][0]["name"] == "Sunken Crypt of Arnor"

    # 3. Query filtered by type
    filtered = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches?discovery_type=dungeon",
        headers={"x-user-id": player_id},
    ).json()
    assert len(filtered["discoveries"]) == 1

    empty_filter = client.get(
        f"/api/v1/campaigns/{campaign_id}/west-marches?discovery_type=outpost",
        headers={"x-user-id": player_id},
    ).json()
    assert len(empty_filter["discoveries"]) == 0
