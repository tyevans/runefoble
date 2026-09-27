"""Tests for turf war REST API endpoints, authorization, and territory queries.

Governed by ADR-0002, ADR-0006, Hard Invariant 1 (SpiceDB), and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_platform.redis_bus import MockAsyncRedis
from the_watcher.dependencies import STREAM_WORLD

from .conftest import setup_campaign_roles


@pytest.mark.asyncio
async def test_zanzibar_turf_war_authorization(client: TestClient):
    """Verify Zanzibar authorization: non-DMs cannot simulate skirmishes; DMs can."""
    camp_id, dm_user, player_user = await setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "West River Gate",
        "attacker": {"faction_id": "ironfang", "military_strength": 30},
        "defender": {"faction_id": "guard", "military_strength": 20},
        "terrain": "plains",
    }

    # Unauthorized player -> 403 Forbidden
    res_player = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": player_user},
    )
    assert res_player.status_code == 403
    assert "Forbidden" in res_player.json()["detail"]

    # Authorized DM -> 200 OK
    res_dm = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res_dm.status_code == 200
    data = res_dm.json()
    assert data["region_id"] == region_id
    assert data["contested_node"] == "West River Gate"


@pytest.mark.asyncio
async def test_turf_war_api_conflict_initiation_and_state_query(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Verify conflict initiation REST API and territory state query endpoints."""
    camp_id, dm_user, player_user = await setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "Smugglers Cove",
        "attacker": {"faction_id": "blood_corsairs", "military_strength": 50, "morale_modifier": 2},
        "defender": {"faction_id": "harbor_militia", "military_strength": 20, "defense_rating": 2},
        "terrain": "plains",
        "attacker_roll": 18,
        "defender_roll": 4,
    }

    res = client.post(
        "/api/v1/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    sim_data = res.json()
    assert sim_data["controlling_faction_id"] == "blood_corsairs"
    assert sim_data["territory_captured"] is True

    # Query territory state via /the-watcher and /api/v1 endpoints
    res_get = client.get(
        f"/the-watcher/regions/{region_id}/unrest?campaign_id={camp_id}",
        headers={"X-User-Id": player_user},
    )
    assert res_get.status_code == 200
    state = res_get.json()
    assert state["controlling_faction_id"] == "blood_corsairs"
    assert "Smugglers Cove" in state["contested_nodes"]
    assert len(state["recent_skirmishes"]) == 1

    # Verify event stream dispatch
    assert STREAM_WORLD in mock_redis.streams
    assert len(mock_redis.streams[STREAM_WORLD]) >= 2
