"""Blackbox tests for haven router modular decomposition and backward compatibility.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.mark.asyncio
async def test_haven_modular_routes_frontdoor_journey(
    session_client: TestClient, spicedb: MockSpiceDBClient
):
    """Verify full haven lifecycle, establishment creation, and tier upgrading through frontdoor."""
    cid, dm_id = str(uuid4()), f"dm_{uuid4().hex[:6]}"
    await spicedb.write_relationship("campaign", cid, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", cid, "player", "user", dm_id)
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"}

    # 1. Haven creation via havens_router
    found_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Havenwood", "scale": "hamlet", "districts": ["commons"], "prosperity": 120},
        headers=headers,
    )
    assert found_res.status_code == 201
    sid = found_res.json()["settlement_id"]
    assert found_res.json()["name"] == "Havenwood"

    # 2. Establishment construction via establishments_router
    est_res = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "commons", "category": "hospitality", "name": "The Green Dragon"},
        headers=headers,
    )
    assert est_res.status_code == 201
    eid = est_res.json()["establishment_id"]

    # 3. Upgrade tier via upgrades_router
    upg_res = session_client.post(
        f"/api/v1/settlements/{sid}/upgrade-tier",
        json={"new_tier": 2, "prosperity": 120},
        headers=headers,
    )
    assert upg_res.status_code == 200
    assert upg_res.json()["tier"] == 2
    assert upg_res.json()["scale"] == "village"

    # 4. Upgrade establishment via upgrades_router
    est_upg = session_client.post(
        f"/api/v1/establishments/{eid}/upgrade",
        json={"tier": 2, "added_amenities": ["cellar"]},
        headers=headers,
    )
    assert est_upg.status_code == 200
    assert est_upg.json()["tier"] == 2
