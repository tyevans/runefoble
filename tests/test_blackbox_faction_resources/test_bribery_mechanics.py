"""Tests for faction bribery mechanics, difficulty thresholds, and counter-bribes.

Governed by ADR-0003, ADR-0006, ADR-0007, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from .conftest import setup_campaign_roles


@pytest.mark.asyncio
async def test_frontdoor_bribery_resolution_mechanics(client: TestClient):
    """Verify bribery difficulty thresholds against target loyalty and counter-bribes."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    fid = f"fact-{uuid4().hex[:8]}"

    client.post(
        f"/factions/{fid}/resources/adjust",
        json={"treasury_delta": 400, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )

    # 1. Bribe corruptible dock official with 100 gold
    bribe_payload = {
        "target_name": "Clerk Garrow",
        "target_role": "official",
        "bribe_amount": 100,
        "target_loyalty": "corruptible",
        "roll": 12,
        "campaign_id": camp_id,
    }
    bribe_res = client.post(
        f"/factions/{fid}/bribery/resolve", json=bribe_payload, headers={"X-User-Id": dm_user}
    )
    assert bribe_res.status_code == 200 and bribe_res.json()["outcome"] == "success"
    assert bribe_res.json()["remaining_treasury"] == 400

    # 2. Bribe loyal guard captain countered by rival counter-bribe
    counter_payload = {
        "target_name": "Captain Vane",
        "target_role": "guard_captain",
        "bribe_amount": 50,
        "target_loyalty": "loyal",
        "counter_bribe": 150,
        "roll": 10,
        "campaign_id": camp_id,
    }
    c_res = client.post(
        f"/factions/{fid}/bribery/resolve", json=counter_payload, headers={"X-User-Id": dm_user}
    )
    assert c_res.status_code == 200 and c_res.json()["outcome"] == "countered"

    # 3. Critical success on natural 20
    crit = client.post(
        f"/factions/{fid}/bribery/resolve",
        json={
            "target_name": "Judge",
            "target_role": "judge",
            "bribe_amount": 50,
            "roll": 20,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert crit.status_code == 200 and crit.json()["outcome"] == "critical_success"

    # 4. Critical failure on natural 1
    fail = client.post(
        f"/factions/{fid}/bribery/resolve",
        json={
            "target_name": "Guard",
            "target_role": "guard",
            "bribe_amount": 50,
            "roll": 1,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert fail.status_code == 200 and fail.json()["outcome"] == "critical_failure"

    # 5. Insufficient treasury check
    broke = client.post(
        f"/factions/{fid}/bribery/resolve",
        json={"target_name": "Guildmaster", "bribe_amount": 5000, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )
    assert broke.status_code == 400 and "Insufficient treasury" in broke.json()["detail"]


@pytest.mark.asyncio
async def test_bribery_unauthorized_access(client: TestClient):
    """Verify non-DM players cannot execute bribery."""
    camp_id, _, player_user = await setup_campaign_roles()
    fid = f"fact-{uuid4().hex[:8]}"

    res = client.post(
        f"/factions/{fid}/bribery/resolve",
        json={"target_name": "Guard Captain", "bribe_amount": 50, "campaign_id": camp_id},
        headers={"X-User-Id": player_user},
    )
    assert res.status_code == 403 and "Forbidden" in res.json()["detail"]
