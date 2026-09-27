"""Tests for faction mercenary recruitment, unit tiers, costs, and upkeep deduction.

Governed by ADR-0003, ADR-0007, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from .conftest import setup_campaign_roles


@pytest.mark.asyncio
async def test_frontdoor_mercenary_recruiting_and_upkeep(client: TestClient):
    """Verify hiring mercenaries updates troop counts, calculates upkeep, and rejects deficits."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    faction_id = f"fact-{uuid4().hex[:8]}"

    # Set initial treasury to 200
    client.post(
        f"/factions/{faction_id}/resources/adjust",
        json={"treasury_delta": 100, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )

    # Recruit 4 heavy infantry at 25 gold each (100 total, upkeep 2 each)
    rec_res = client.post(
        f"/factions/{faction_id}/mercenaries/recruit",
        json={
            "unit_name": "Black Skull Enforcers",
            "count": 4,
            "cost_per_unit": 25,
            "unit_type": "heavy_infantry",
            "upkeep_per_tick": 2,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["treasury"] == 100  # 200 - 100
    assert data["mercenaries_count"] == 4
    assert data["upkeep_cost"] == 8  # 4 * 2

    # Attempt to recruit beyond treasury (needs 150, only has 100) -> 400 Bad Request
    fail_res = client.post(
        f"/factions/{faction_id}/mercenaries/recruit",
        json={
            "unit_name": "Siege Engineers",
            "count": 3,
            "cost_per_unit": 50,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert fail_res.status_code == 400
    assert "Insufficient treasury" in fail_res.json()["detail"]


@pytest.mark.asyncio
async def test_mercenary_recruitment_unauthorized(client: TestClient):
    """Verify non-DM players cannot recruit mercenaries."""
    camp_id, _, player_user = await setup_campaign_roles()
    faction_id = f"fact-{uuid4().hex[:8]}"

    res = client.post(
        f"/factions/{faction_id}/mercenaries/recruit",
        json={"unit_name": "Archers", "count": 2, "cost_per_unit": 10, "campaign_id": camp_id},
        headers={"X-User-Id": player_user},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]
