"""Blackbox tests for West Marches discovery synchronization across parties.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import STREAM_WEST_MARCHES
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis


async def _setup_world(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    officer: str,
    parties: list[tuple[str, str, str]],
    name: str = "The Sunken Marches",
) -> str:
    res = client.post("/api/v1/shared-worlds", json={"name": name}, headers={"x-user-id": officer})
    wid = res.json()["shared_world_id"]
    for cid, uid, pname in parties:
        await spicedb.write_relationship("campaign", cid, "player", "user", uid)
        client.post(
            f"/api/v1/shared-worlds/{wid}/campaigns",
            json={"campaign_id": cid, "party_name": pname},
            headers={"x-user-id": officer},
        )
    return wid


@pytest.mark.asyncio
async def test_blackbox_west_marches_shared_frontier_and_cross_party_discoveries(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb_client: MockSpiceDBClient,
    party_ids: dict[str, str],
):
    """Test Scenario 1 (US-0058): Cross-Party Discovery Synchronization."""
    officer_id = party_ids["officer"]
    blue_uid, gold_uid = party_ids["blue_player"], party_ids["gold_player"]
    c_blue, c_gold = party_ids["campaign_blue"], party_ids["campaign_gold"]

    world_id = await _setup_world(
        client,
        spicedb_client,
        officer_id,
        [(c_blue, blue_uid, "Party Blue"), (c_gold, gold_uid, "Party Gold")],
    )

    discovery_payload = {
        "name": "Sunken Crypt of Arnor",
        "discovery_type": "dungeon",
        "coordinates": {"x": 145.0, "y": 280.0},
        "discovered_by_campaign_id": c_blue,
        "discovered_by_party_name": "Party Blue",
        "danger_level": 4,
        "metadata": {"entrance": "submerged_tunnel", "biome": "bog"},
    }
    disc_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/discoveries",
        json=discovery_payload,
        headers={"x-user-id": blue_uid},
    )
    assert disc_res.status_code == 201
    disc_data = disc_res.json()["discovery"]
    assert disc_data["name"] == "Sunken Crypt of Arnor"
    assert disc_data["discovered_by_party_name"] == "Party Blue"
    assert "timestamp" in disc_data

    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any("CrossCampaignDiscoveryShared" in str(entry[1]) for entry in entries)

    gold_query = client.get(
        f"/api/v1/shared-worlds/{world_id}/discoveries",
        headers={"x-user-id": gold_uid},
    )
    assert gold_query.status_code == 200
    discoveries = gold_query.json()["discoveries"]
    assert len(discoveries) == 1
    found = discoveries[0]
    assert found["name"] == "Sunken Crypt of Arnor"
    assert found["discovered_by_party_name"] == "Party Blue"
    assert found["coordinates"] == {"x": 145.0, "y": 280.0}
    assert found["metadata"]["entrance"] == "submerged_tunnel"


@pytest.mark.asyncio
async def test_shared_landmark_discovery_and_filtering(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
    party_ids: dict[str, str],
):
    """Test fog-of-war landmark recording and discovery type filtering."""
    officer_id = party_ids["officer"]
    blue_uid = party_ids["blue_player"]
    c_blue = party_ids["campaign_blue"]

    world_id = await _setup_world(
        client, spicedb_client, officer_id, [(c_blue, blue_uid, "Party Blue")], "Whispering Crags"
    )

    client.post(
        f"/api/v1/shared-worlds/{world_id}/discoveries",
        json={
            "name": "Obsidian Spire",
            "discovery_type": "landmark",
            "coordinates": {"x": 30.0, "y": 90.0},
            "discovered_by_campaign_id": c_blue,
            "discovered_by_party_name": "Party Blue",
        },
        headers={"x-user-id": blue_uid},
    )
    filtered = client.get(
        f"/api/v1/shared-worlds/{world_id}/discoveries?discovery_type=landmark",
        headers={"x-user-id": blue_uid},
    ).json()["discoveries"]
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Obsidian Spire"

    empty = client.get(
        f"/api/v1/shared-worlds/{world_id}/discoveries?discovery_type=dungeon",
        headers={"x-user-id": blue_uid},
    ).json()["discoveries"]
    assert len(empty) == 0
