"""Blackbox tests for milestone pin placement, era filtering, and Zanzibar authorization.

Governed by ADR-0001, ADR-0007, and Hard Invariant 7.
"""

from uuid import UUID

import pytest
from campaign_lore.dependencies import get_atlas_repo
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient


@pytest.mark.asyncio
async def test_milestone_pin_placement_and_retrieval(
    client: TestClient, spicedb: SpiceDBClient, campaign_id: str
):
    """Test milestone pin placement and frontdoor retrieval."""
    user_id = "rowan_chronicler"
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", user_id)
    url = f"/api/v1/campaigns/{campaign_id}/atlas/pins"
    payload = {
        "title": "Silverkeep Garrison Liberation",
        "coordinates": {"x": 200.0, "y": 200.0},
        "layer": "continental",
        "description": "Party liberated the garrison from the shadow legion.",
        "era": "Session 12: Liberation",
        "session_id": "session-12",
        "linked_entity_ids": ["entity-silverguard"],
        "metadata": {"icon": "castle_flag"},
    }
    resp = client.post(url, json=payload, headers={"x-user-id": user_id})
    assert resp.status_code == 201
    pin_id = resp.json()["pin_id"]
    assert resp.json()["title"] == "Silverkeep Garrison Liberation"

    aggregate = await get_atlas_repo().load(UUID(campaign_id))
    assert len(aggregate.state.pins) == 1
    assert aggregate.state.pins[0]["pin_id"] == pin_id

    get_resp = client.get(f"{url}/{pin_id}", headers={"x-user-id": user_id})
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Silverkeep Garrison Liberation"


@pytest.mark.asyncio
async def test_milestone_pin_era_and_session_filtering(
    client: TestClient, spicedb: SpiceDBClient, campaign_id: str
):
    """Test chronological era and session filtering for atlas milestone pins."""
    user_id = "rowan_chronicler"
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", user_id)
    base, headers = f"/api/v1/campaigns/{campaign_id}/atlas", {"x-user-id": user_id}

    client.post(
        f"{base}/pins",
        json={
            "title": "Ancient Sunken Ruins",
            "coordinates": {"x": 50.0, "y": 80.0},
            "layer": "continental",
            "era": "Age of Ash",
            "session_id": "session-1",
        },
        headers=headers,
    )
    client.post(
        f"{base}/pins",
        json={
            "title": "Citadel of the Dawn",
            "coordinates": {"x": 450.0, "y": 600.0},
            "layer": "continental",
            "era": "Age of Rebirth",
            "session_id": "session-20",
        },
        headers=headers,
    )

    full = client.get(f"{base}?layer=continental", headers=headers).json()
    assert len(full["pins"]) == 2

    ash = client.get(f"{base}?layer=continental&era=Age of Ash", headers=headers).json()
    assert len(ash["pins"]) == 1 and ash["pins"][0]["title"] == "Ancient Sunken Ruins"

    sess = client.get(f"{base}?layer=continental&session_id=session-20", headers=headers).json()
    assert len(sess["pins"]) == 1 and sess["pins"][0]["title"] == "Citadel of the Dawn"


@pytest.mark.asyncio
async def test_milestone_pin_zanzibar_permission_checks(
    client: TestClient, spicedb: SpiceDBClient, campaign_id: str
):
    """Test SpiceDB Zanzibar denies unauthorized users from viewing or creating pins."""
    intruder = "eve_intruder"
    resp = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins",
        json={"title": "Intrusion Pin", "coordinates": {"x": 10.0, "y": 10.0}},
        headers={"x-user-id": intruder},
    )
    assert resp.status_code == 403

    view_resp = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas",
        headers={"x-user-id": intruder},
    )
    assert view_resp.status_code == 403
