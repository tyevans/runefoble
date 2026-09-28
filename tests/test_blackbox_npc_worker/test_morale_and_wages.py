"""Blackbox frontdoor tests for NPC worker wage payouts, morale calculation, and mood swings.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_event_emitted


@pytest.mark.asyncio
async def test_blackbox_worker_wages_and_operating_cost(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify worker wages aggregate into establishment net operating cost."""
    campaign_id, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", dm_id)
    h = {"x-user-id": dm_id}

    s_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Oakhaven", "districts": ["commons"]},
        headers=h,
    )
    s_id = s_res.json()["settlement_id"]
    est_payload = {
        "district_id": "commons",
        "category": "commerce",
        "name": "Mill",
        "operating_cost": 20,
    }
    est_res = client.post(f"/api/v1/settlements/{s_id}/establishments", json=est_payload, headers=h)
    est_id = est_res.json()["establishment_id"]

    for name, role, wage in [("Miller John", "miller", 6), ("Pip", "apprentice", 9)]:
        client.post(
            f"/api/v1/establishments/{est_id}/workers",
            json={"name": name, "role": role, "wage": wage},
            headers=h,
        )

    ops = client.get(f"/api/v1/establishments/{est_id}", headers=h).json()
    assert ops["staff_count"] == 2 and ops["total_wages"] == 15 and ops["net_operating_cost"] == 35


@pytest.mark.asyncio
async def test_blackbox_morale_swings_and_grievance_escalation(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Test worker mood updates, patience degradation, morale drop, and authorization."""
    campaign_id, dm_id, intruder_id = str(uuid4()), "dm_morale", "intruder_morale"
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", dm_id)
    h = {"x-user-id": dm_id}

    s_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Riverdale", "districts": ["commons"]},
        headers=h,
    )
    s_id = s_res.json()["settlement_id"]
    est_payload = {
        "district_id": "commons",
        "category": "hospitality",
        "name": "Bakery",
        "operating_cost": 5,
    }
    est_res = client.post(f"/api/v1/settlements/{s_id}/establishments", json=est_payload, headers=h)
    est_id = est_res.json()["establishment_id"]

    worker_payload = {"name": "Marta", "role": "baker", "mood": "cheerful", "patience": 8}
    worker = client.post(
        f"/api/v1/establishments/{est_id}/workers", json=worker_payload, headers=h
    ).json()
    npc_id = worker["npc_id"]
    init_q = client.get(f"/api/v1/establishments/{est_id}", headers=h).json()[
        "projected_service_quality"
    ]

    # Unauthorized user cannot modify worker mood
    bad_mood = {"mood": "hostile", "temperament": "Furious"}
    unauth = client.patch(
        f"/api/v1/npcs/{npc_id}/mood", json=bad_mood, headers={"x-user-id": intruder_id}
    )
    assert unauth.status_code == 403

    # Grievance escalation: unpaid wages trigger desperate mood and patience loss
    patch_body = {
        "mood": "desperate",
        "temperament": "Anxious",
        "patience_delta": -4,
        "metadata": {"grievance": "unpaid_wages"},
    }
    patch_res = client.patch(f"/api/v1/npcs/{npc_id}/mood", json=patch_body, headers=h)
    assert patch_res.status_code == 200 and patch_res.json()["patience"] == 4
    assert_event_emitted(mock_bus, "NPCMoodUpdated")

    updated_q = client.get(f"/api/v1/establishments/{est_id}", headers=h).json()[
        "projected_service_quality"
    ]
    assert updated_q < init_q
