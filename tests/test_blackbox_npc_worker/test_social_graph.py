"""Blackbox frontdoor tests for NPC worker social graph, relationship synergy, and friction.

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
async def test_blackbox_social_graph_edges_and_redstring_serialization(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Verify relationship formation emits domain events and serializes to redstring graph edges."""
    campaign_id, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", dm_id)
    h = {"x-user-id": dm_id}

    s_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Ironhaven", "districts": ["artisan_quarter"]},
        headers=h,
    )
    s_id = s_res.json()["settlement_id"]
    est_payload = {"district_id": "artisan_quarter", "category": "commerce", "name": "Anvil"}
    est_res = client.post(f"/api/v1/settlements/{s_id}/establishments", json=est_payload, headers=h)
    est_id = est_res.json()["establishment_id"]

    worker_payload = {
        "name": "Torvin",
        "role": "armorer",
        "relationships": [{"target_npc": "marta", "relation": "debtor", "intensity": 0.5}],
    }
    worker = client.post(
        f"/api/v1/establishments/{est_id}/workers", json=worker_payload, headers=h
    ).json()
    npc_id = worker["npc_id"]
    assert_event_emitted(mock_bus, "NPCRelationshipFormed")

    # Form secondary mentor tie
    mentor_payload = {"target_npc": "leo", "relation": "mentor", "intensity": 0.8}
    rel_res = client.post(f"/api/v1/npcs/{npc_id}/relationships", json=mentor_payload, headers=h)
    assert rel_res.status_code == 201 and len(rel_res.json()["relationships"]) == 2

    # Query full roster to inspect redstring-compatible edges
    roster = client.get(f"/api/v1/establishments/{est_id}/roster", headers=h).json()
    assert len(roster["social_graph_edges"]) >= 2
    edge = roster["social_graph_edges"][0]
    assert edge["source_id"] == npc_id and edge["target_id"] == "marta" and edge["confidence"] > 0.8


@pytest.mark.asyncio
async def test_blackbox_rival_friction_and_friendship_synergy(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify workplace friction from rival ties increases tension vs friendship reducing tension."""
    campaign_id, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", dm_id)
    h = {"x-user-id": dm_id}

    s_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Haven", "districts": ["commons"]},
        headers=h,
    )
    s_id = s_res.json()["settlement_id"]
    est_payload = {"district_id": "commons", "category": "hospitality", "name": "Tavern"}
    est_res = client.post(f"/api/v1/settlements/{s_id}/establishments", json=est_payload, headers=h)
    est_id = est_res.json()["establishment_id"]

    workers = [
        client.post(
            f"/api/v1/establishments/{est_id}/workers",
            json={"name": name, "role": role},
            headers=h,
        ).json()
        for name, role in [("Staff A", "cook"), ("Staff B", "server")]
    ]
    w1, w2 = workers[0], workers[1]

    # Form rival relationship between peer coworkers -> friction increases tension
    client.post(
        f"/api/v1/npcs/{w1['npc_id']}/relationships",
        json={"target_npc": w2["npc_id"], "relation": "rival", "intensity": 0.9},
        headers=h,
    )
    rival_roster = client.get(f"/api/v1/establishments/{est_id}/roster", headers=h).json()
    rival_tension = rival_roster["operations"]["interpersonal_tension_index"]

    # Reconcile relationship to friend / ally -> friendship synergy reduces tension
    client.post(
        f"/api/v1/npcs/{w1['npc_id']}/relationships",
        json={"target_npc": w2["npc_id"], "relation": "friend", "intensity": 0.9},
        headers=h,
    )
    friend_roster = client.get(f"/api/v1/establishments/{est_id}/roster", headers=h).json()
    friend_tension = friend_roster["operations"]["interpersonal_tension_index"]
    assert friend_tension < rival_tension
