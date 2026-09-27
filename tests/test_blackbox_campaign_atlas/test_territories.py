"""Blackbox tests for geopolitical territory boundaries and containment.

Governed by ADR-0001, ADR-0007, and Hard Invariant 7.
"""

from uuid import UUID

import pytest
from campaign_lore.dependencies import get_atlas_repo
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient


@pytest.mark.asyncio
async def test_territory_definition_and_polygon_containment(
    client: TestClient,
    spicedb: SpiceDBClient,
    campaign_id: str,
    silverkeep_polygon: list[list[float]],
):
    """Test geopolitical boundary definition and automated point-in-polygon containment."""
    user_id = "rowan_chronicler"
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", user_id)

    terr_payload = {
        "name": "Silverkeep Garrison",
        "layer": "continental",
        "polygon_coordinates": silverkeep_polygon,
        "owner_faction": "Silverguard Alliance",
        "is_contested": True,
        "era": "Session 12: Liberation",
        "metadata": {"banner_color": "#4361ee"},
    }
    terr_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/territories",
        json=terr_payload,
        headers={"x-user-id": user_id},
    )
    assert terr_resp.status_code == 201, terr_resp.text
    terr_data = terr_resp.json()
    assert terr_data["name"] == "Silverkeep Garrison"
    assert terr_data["is_contested"] is True
    territory_id = terr_data["territory_id"]

    pin_payload = {
        "title": "Silverkeep Garrison Liberation",
        "coordinates": {"x": 200.0, "y": 200.0},
        "layer": "continental",
        "description": "Party liberated the garrison.",
        "era": "Session 12: Liberation",
        "session_id": "session-12",
        "linked_entity_ids": ["entity-silverguard"],
        "metadata": {"icon": "castle_flag"},
    }
    pin_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins",
        json=pin_payload,
        headers={"x-user-id": user_id},
    )
    assert pin_resp.status_code == 201, pin_resp.text
    pin_data = pin_resp.json()
    assert pin_data["metadata"]["territory_id"] == territory_id
    assert pin_data["metadata"]["territory_name"] == "Silverkeep Garrison"
    assert "normalized_coordinates" in pin_data["metadata"]

    aggregate = await get_atlas_repo().load(UUID(campaign_id))
    assert len(aggregate.state.pins) == 1
    assert len(aggregate.state.territories) == 1


@pytest.mark.asyncio
async def test_contested_territory_updates_and_layer_toggle(
    client: TestClient, spicedb: SpiceDBClient, campaign_id: str
):
    """Test contested territory detection and layer visibility toggle."""
    user_id = "rowan_chronicler"
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", user_id)

    terr_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/territories",
        json={
            "name": "Obsidian Borderlands",
            "layer": "continental",
            "polygon_coordinates": [[400.0, 500.0], [600.0, 500.0], [500.0, 700.0]],
            "owner_faction": "Disputed",
            "is_contested": True,
            "era": "Age of Rebirth",
        },
        headers={"x-user-id": user_id},
    )
    assert terr_resp.status_code == 201

    full_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas?layer=continental",
        headers={"x-user-id": user_id},
    )
    assert full_resp.status_code == 200
    full_data = full_resp.json()
    assert len(full_data["contested_zones"]) == 1
    assert full_data["contested_zones"][0]["name"] == "Obsidian Borderlands"
    assert full_data["layer_extent"] == 1000.0

    toggle_resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/layers/toggle",
        json={"layer": "municipal", "is_visible": False},
        headers={"x-user-id": user_id},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_visible"] is False
