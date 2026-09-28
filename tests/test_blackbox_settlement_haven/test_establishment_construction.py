"""Blackbox tests for establishment construction across functional categories.

Governed by ADR-0001, ADR-0007, ADR-0008, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient


@pytest.mark.asyncio
async def test_construct_establishments_across_all_categories(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify constructing establishments across Hospitality, Commerce, Civic, Faith, and Underworld."""
    cid, uid = str(uuid4()), f"mayor_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", uid)

    districts = ["commons", "bazaar", "sanctuary", "forum", "shadows"]
    s_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "HavenPort", "scale": "market_town", "districts": districts},
        headers={"x-user-id": uid},
    )
    sid = s_res.json()["settlement_id"]

    categories = [
        ("hospitality", "The Drunken Dragon Inn", "commons"),
        ("commerce", "The Warm Hearth Bakery", "bazaar"),
        ("civic", "Town Hall & Registry", "forum"),
        ("faith", "Shrine of the Silver Dawn", "sanctuary"),
        ("underworld", "The Velvet Den", "shadows"),
    ]
    for category, name, district in categories:
        res = client.post(
            f"/api/v1/settlements/{sid}/establishments",
            json={
                "district_id": district,
                "category": category,
                "name": name,
                "capacity": 25,
                "operating_cost": 5,
            },
            headers={"x-user-id": uid},
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert (
            data["category"] == category
            and data["name"] == name
            and data["district_id"] == district
        )

    # Verify all 5 establishments appear in settlement projection
    proj = client.get(f"/api/v1/campaigns/{cid}/settlements/{sid}", headers={"x-user-id": uid})
    assert len(proj.json()["establishments"]) == 5


@pytest.mark.asyncio
async def test_establishment_construction_invariants_and_auth(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify district zoning invariants, capacity validation, and authorization."""
    cid, uid = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    intruder_id = f"intruder_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "dungeon_master", "user", uid)

    s_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Fortress", "scale": "village", "districts": ["commons", "trading_post"]},
        headers={"x-user-id": uid},
    )
    sid = s_res.json()["settlement_id"]

    # Construction in an unzoned/locked district -> 400
    unzoned = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "forbidden_citadel", "category": "civic", "name": "Citadel"},
        headers={"x-user-id": uid},
    )
    assert unzoned.status_code == 400 and "not zoned or unlocked" in unzoned.json()["detail"]

    # Invalid capacity <= 0 -> 400
    bad_cap = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "commerce", "name": "Shop", "capacity": 0},
        headers={"x-user-id": uid},
    )
    assert bad_cap.status_code == 400

    # Intruder construction -> 403 Forbidden
    denied = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "underworld", "name": "Den"},
        headers={"x-user-id": intruder_id},
    )
    assert denied.status_code == 403
