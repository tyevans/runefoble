"""Blackbox tests for cross-campaign settlement visibility and SpiceDB isolation.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient


@pytest.mark.asyncio
async def test_blackbox_cross_campaign_haven_sharing_and_co_upgrading(
    client: TestClient,
    spicedb: MockSpiceDBClient,
):
    """Test Scenario: Two adventuring campaigns share and co-upgrade a communal frontier haven."""
    officer = "officer_kael"
    blue_player = "ranger_lyra"
    gold_player = "paladin_gawain"
    camp_blue = str(uuid4())
    camp_gold = str(uuid4())

    # Establish shared world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "The Sunken Marches", "frontier_region": "Shadowed Fenlands"},
        headers={"x-user-id": officer},
    )
    world_id = world_res.json()["shared_world_id"]

    # Register both campaigns and players in shared world
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", blue_player)
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", gold_player)
    await spicedb.write_relationship("campaign", camp_blue, "player", "user", blue_player)
    await spicedb.write_relationship("campaign", camp_gold, "player", "user", gold_player)

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": camp_blue, "party_name": "Party Blue"},
        headers={"x-user-id": officer},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": camp_gold, "party_name": "Party Gold"},
        headers={"x-user-id": officer},
    )

    # Party Blue charters an outpost
    charter_res = client.post(
        "/settlements",
        json={
            "name": "Azure Redoubt",
            "shared_world_id": world_id,
            "settlement_type": "haven",
            "founded_by_campaign_id": camp_blue,
        },
        headers={"x-user-id": blue_player},
    )
    assert charter_res.status_code == 201
    sid = charter_res.json()["settlement_id"]

    # Party Gold queries and views Azure Redoubt through the shared world link
    gold_view = client.get(f"/settlements/{sid}", headers={"x-user-id": gold_player})
    assert gold_view.status_code == 200
    assert gold_view.json()["name"] == "Azure Redoubt"

    # Party Gold contributes materials to upgrade Azure Redoubt's watchtower
    gold_upgrade = client.post(
        f"/settlements/{sid}/upgrade",
        json={
            "facility_id": "watchtower",
            "contributing_campaign_id": camp_gold,
            "gold_spent": 120,
            "materials_spent": {"hardwood": 15},
        },
        headers={"x-user-id": gold_player},
    )
    assert gold_upgrade.status_code == 200
    up_data = gold_upgrade.json()
    assert up_data["facilities"]["watchtower"] == 2
    assert camp_blue in up_data["contributing_campaigns"]
    assert camp_gold in up_data["contributing_campaigns"]


@pytest.mark.asyncio
async def test_blackbox_unauthorized_outsider_isolation(
    client: TestClient,
    spicedb: MockSpiceDBClient,
):
    """Test Scenario: Malicious or unlinked outsiders are forbidden by SpiceDB Zanzibar."""
    officer = "officer_kael"
    blue_player = "ranger_lyra"
    outsider = "stranger_malicious"
    camp_blue = str(uuid4())

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Outskirts"},
        headers={"x-user-id": officer},
    )
    world_id = world_res.json()["shared_world_id"]
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", blue_player)
    await spicedb.write_relationship("campaign", camp_blue, "player", "user", blue_player)

    charter_res = client.post(
        "/settlements",
        json={
            "name": "Solitary Haven",
            "shared_world_id": world_id,
            "founded_by_campaign_id": camp_blue,
        },
        headers={"x-user-id": blue_player},
    )
    sid = charter_res.json()["settlement_id"]

    # Outsider cannot view the haven
    h_out = {"x-user-id": outsider}
    assert client.get(f"/settlements/{sid}", headers=h_out).status_code == 403

    # Outsider cannot upgrade the haven
    bad_up = client.post(
        f"/settlements/{sid}/upgrade",
        json={"facility_id": "workshop", "gold_spent": 50},
        headers=h_out,
    )
    assert bad_up.status_code == 403

    # Outsider cannot charter havens in a shared world they do not belong to
    bad_charter = client.post(
        "/settlements",
        json={"name": "Hostile Fort", "shared_world_id": world_id},
        headers=h_out,
    )
    assert bad_charter.status_code == 403
