"""Blackbox frontdoor tests for NPC worker assignment, role compatibility, and relieving.

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
async def test_blackbox_worker_assignment_and_role_compatibility(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Assign workers, verify role compatibility service boost, roster, and relieving."""
    camp_id, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", camp_id, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", camp_id, "player", "user", dm_id)
    h = {"x-user-id": dm_id}

    s_res = client.post(
        f"/api/v1/campaigns/{camp_id}/settlements",
        json={"name": "Ironhaven", "districts": ["artisan_quarter"]},
        headers=h,
    )
    s_id = s_res.json()["settlement_id"]
    est_res = client.post(
        f"/api/v1/settlements/{s_id}/establishments",
        json={"district_id": "artisan_quarter", "category": "commerce", "name": "The Ember Anvil"},
        headers=h,
    )
    est_id = est_res.json()["establishment_id"]

    # Assign worker with matching trade proficiencies (role compatibility boost)
    armorer_res = client.post(
        f"/api/v1/establishments/{est_id}/workers",
        json={
            "name": "Torvin Ironbreaker",
            "role": "armorer",
            "wage": 8,
            "trade_proficiencies": ["blacksmithing", "armorer"],
            "shelf_inventory": [{"item_id": "plate", "stock": 2, "price_gp": 150}],
        },
        headers=h,
    )
    assert armorer_res.status_code == 201
    torvin = armorer_res.json()
    assert torvin["service_quality_contribution"] > 1.2
    assert_event_emitted(mock_bus, "NPCWorkerAssigned")

    # Verify roster listing
    roster_res = client.get(f"/api/v1/establishments/{est_id}/workers", headers=h)
    assert roster_res.status_code == 200 and len(roster_res.json()) == 1

    # Relieve worker from duty
    relieve_res = client.post(
        f"/api/v1/establishments/{est_id}/workers/{torvin['npc_id']}/relieve",
        json={"reason": "Contract concluded"},
        headers=h,
    )
    assert relieve_res.status_code == 200 and relieve_res.json()["status"] == "relieved"
    assert_event_emitted(mock_bus, "NPCWorkerRelieved")

    # Active roster is now empty
    active_roster = client.get(f"/api/v1/establishments/{est_id}/workers", headers=h)
    assert len(active_roster.json()) == 0


@pytest.mark.asyncio
async def test_blackbox_worker_assignment_authorization(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify SpiceDB Zanzibar permissions restrict worker assignment and management."""
    camp_id, owner_id, intruder_id = str(uuid4()), "owner_1", "intruder_1"
    await spicedb.write_relationship("campaign", camp_id, "dungeon_master", "user", owner_id)
    await spicedb.write_relationship("campaign", camp_id, "player", "user", owner_id)

    s_id = client.post(
        f"/api/v1/campaigns/{camp_id}/settlements",
        json={"name": "Oasis Haven", "districts": ["commons"]},
        headers={"x-user-id": owner_id},
    ).json()["settlement_id"]

    est_id = client.post(
        f"/api/v1/settlements/{s_id}/establishments",
        json={"district_id": "commons", "category": "hospitality", "name": "The Dune Flagon"},
        headers={"x-user-id": owner_id},
    ).json()["establishment_id"]

    # Unauthorized user assignment fails with 403
    unauth_assign = client.post(
        f"/api/v1/establishments/{est_id}/workers",
        json={"name": "Boris Bouncer", "role": "bouncer"},
        headers={"x-user-id": intruder_id},
    )
    assert unauth_assign.status_code == 403
