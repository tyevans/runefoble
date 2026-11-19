"""Blackbox tests for establishment construction across functional categories.

Governed by ADR-0001, ADR-0007, ADR-0008, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_construct_establishments_across_all_categories(client: TestClient) -> None:
    """Verify constructing establishments across Hospitality, Commerce, Civic, Faith, and Underworld."""
    owner_id, uid = f"owner_{uuid4().hex[:8]}", f"mayor_{uuid4().hex[:8]}"
    cid = create_campaign(client, owner_id)
    invite_and_join(client, cid, owner_id, uid, "player")

    districts = ["commons", "bazaar", "sanctuary", "forum", "shadows"]
    s_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "HavenPort", "scale": "market_town", "districts": districts},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"},
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
            headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"},
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert (
            data["category"] == category
            and data["name"] == name
            and data["district_id"] == district
        )

    # Verify all 5 establishments appear in settlement projection
    proj = client.get(
        f"/api/v1/campaigns/{cid}/settlements/{sid}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"},
    )
    assert len(proj.json()["establishments"]) == 5


def test_establishment_construction_invariants_and_auth(client: TestClient) -> None:
    """Verify district zoning invariants, capacity validation, and authorization."""
    uid = f"dm_{uuid4().hex[:8]}"
    intruder_id = f"intruder_{uuid4().hex[:8]}"
    cid = create_campaign(client, uid)

    s_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Fortress", "scale": "village", "districts": ["commons", "trading_post"]},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"},
    )
    sid = s_res.json()["settlement_id"]

    # Construction in an unzoned/locked district -> 400
    unzoned = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "forbidden_citadel", "category": "civic", "name": "Citadel"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"},
    )
    assert unzoned.status_code == 400 and "not zoned or unlocked" in unzoned.json()["detail"]

    # Invalid capacity <= 0 -> 400
    bad_cap = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "commerce", "name": "Shop", "capacity": 0},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(uid)}"},
    )
    assert bad_cap.status_code == 400

    # Intruder construction -> 403 Forbidden
    denied = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "underworld", "name": "Den"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(intruder_id)}"},
    )
    assert denied.status_code == 403
