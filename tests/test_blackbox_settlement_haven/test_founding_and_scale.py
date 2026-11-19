"""Blackbox tests for settlement founding, civic scaling, and district capacity.

Governed by ADR-0001, ADR-0007, ADR-0008, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_found_settlement_and_projection_query(client: TestClient) -> None:
    """Verify settlement founding and subsequent projection retrieval."""
    owner_id, mayor_id = f"owner_{uuid4().hex[:8]}", f"mayor_{uuid4().hex[:8]}"
    cid = create_campaign(client, owner_id)
    invite_and_join(client, cid, owner_id, mayor_id, "player")

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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(mayor_id)}"},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    sid = data["settlement_id"]
    assert data["name"] == "Oakhaven" and data["scale"] == "village" and data["tier"] == 2
    assert "agricultural_commons" in data["districts"] and data["prosperity"] == 150

    proj = client.get(
        f"/api/v1/campaigns/{cid}/settlements/{sid}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(mayor_id)}"},
    )
    assert proj.status_code == 200 and proj.json()["settlement_id"] == sid


def test_district_capacity_and_scale_validation(client: TestClient) -> None:
    """Verify district capacity limits per civic scale and scale validation."""
    owner_id, mayor_id = f"owner_{uuid4().hex[:8]}", f"mayor_{uuid4().hex[:8]}"
    cid = create_campaign(client, owner_id)
    invite_and_join(client, cid, owner_id, mayor_id, "player")

    # Hamlet permits at most 2 districts: 3 districts should fail
    cap_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "TooBigHamlet", "scale": "hamlet", "districts": ["d1", "d2", "d3"]},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(mayor_id)}"},
    )
    assert cap_res.status_code == 400
    assert "permits at most 2 districts" in cap_res.json()["detail"]

    # Invalid scale should fail
    scale_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "BadScale", "scale": "invalid_scale"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(mayor_id)}"},
    )
    assert scale_res.status_code == 400
    assert "Invalid settlement scale" in scale_res.json()["detail"]


def test_settlement_authorization_enforcement(client: TestClient) -> None:
    """Verify Zanzibar authorization guards founding and viewing settlements."""
    dm_id, intruder_id = f"dm_{uuid4().hex[:8]}", f"intruder_{uuid4().hex[:8]}"
    cid = create_campaign(client, dm_id)

    # Intruder founding denied
    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Forbidden", "scale": "hamlet"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(intruder_id)}"},
    )
    assert res.status_code == 403

    # DM founding succeeds
    ok_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Lawful Citadel", "scale": "village"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"},
    )
    assert ok_res.status_code == 201
    sid = ok_res.json()["settlement_id"]

    # Intruder viewing denied
    view_res = client.get(
        f"/api/v1/campaigns/{cid}/settlements/{sid}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(intruder_id)}"},
    )
    assert view_res.status_code == 403
