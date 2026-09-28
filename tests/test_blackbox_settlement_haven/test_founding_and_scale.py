"""Blackbox tests for settlement founding, civic scaling, and district capacity.

Governed by ADR-0001, ADR-0007, ADR-0008, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient


@pytest.mark.asyncio
async def test_found_settlement_and_projection_query(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify settlement founding and subsequent projection retrieval."""
    cid, mayor_id = str(uuid4()), f"mayor_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", mayor_id)

    payload = {
        "name": "Oakhaven",
        "scale": "village",
        "biome": "river_confluence",
        "coordinates": {"x": 145.0, "y": 280.5},
        "prosperity": 150,
        "districts": ["commons", "agricultural_commons", "defensive_palisade"],
    }
    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json=payload,
        headers={"x-user-id": mayor_id},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    sid = data["settlement_id"]
    assert data["name"] == "Oakhaven" and data["scale"] == "village" and data["tier"] == 2
    assert "agricultural_commons" in data["districts"] and data["prosperity"] == 150

    proj = client.get(f"/api/v1/campaigns/{cid}/settlements/{sid}", headers={"x-user-id": mayor_id})
    assert proj.status_code == 200 and proj.json()["settlement_id"] == sid


@pytest.mark.asyncio
async def test_district_capacity_and_scale_validation(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify district capacity limits per civic scale and scale validation."""
    cid, mayor_id = str(uuid4()), f"mayor_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", mayor_id)

    # Hamlet permits at most 2 districts: 3 districts should fail
    cap_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "TooBigHamlet", "scale": "hamlet", "districts": ["d1", "d2", "d3"]},
        headers={"x-user-id": mayor_id},
    )
    assert cap_res.status_code == 400
    assert "permits at most 2 districts" in cap_res.json()["detail"]

    # Invalid scale should fail
    scale_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "BadScale", "scale": "invalid_scale"},
        headers={"x-user-id": mayor_id},
    )
    assert scale_res.status_code == 400
    assert "Invalid settlement scale" in scale_res.json()["detail"]


@pytest.mark.asyncio
async def test_settlement_authorization_enforcement(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify Zanzibar authorization guards founding and viewing settlements."""
    cid = str(uuid4())
    dm_id, intruder_id = f"dm_{uuid4().hex[:8]}", f"intruder_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "dungeon_master", "user", dm_id)

    # Intruder founding denied
    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Forbidden", "scale": "hamlet"},
        headers={"x-user-id": intruder_id},
    )
    assert res.status_code == 403

    # DM founding succeeds
    ok_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Lawful Citadel", "scale": "village"},
        headers={"x-user-id": dm_id},
    )
    assert ok_res.status_code == 201
    sid = ok_res.json()["settlement_id"]

    # Intruder viewing denied
    view_res = client.get(
        f"/api/v1/campaigns/{cid}/settlements/{sid}", headers={"x-user-id": intruder_id}
    )
    assert view_res.status_code == 403
