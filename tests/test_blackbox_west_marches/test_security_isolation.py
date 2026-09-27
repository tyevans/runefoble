"""Blackbox tests for SpiceDB Zanzibar multi-party isolation and security.

Governed by ADR-0001 and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient


async def _setup_world(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    officer: str,
    parties: list[tuple[str, str, str]],
    name: str = "Frontier",
) -> str:
    res = client.post(
        "/api/v1/shared-worlds", json={"name": name}, headers={"x-user-id": officer}
    ).json()
    wid = res["shared_world_id"]
    for cid, uid, pname in parties:
        await spicedb.write_relationship("campaign", cid, "player", "user", uid)
        client.post(
            f"/api/v1/shared-worlds/{wid}/campaigns",
            json={"campaign_id": cid, "party_name": pname},
            headers={"x-user-id": officer},
        )
    return wid


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_multi_party_isolation(
    client: TestClient, spicedb_client: MockSpiceDBClient
):
    """Verify ADR-0001: While geography is shared, private character sheets remain isolated."""
    officer_id, blue_player, gold_player = "rowan_officer", "blue_ranger", "gold_paladin"
    outsider = "stranger_malicious"
    c_blue, c_gold, char_blue_id = str(uuid4()), str(uuid4()), str(uuid4())

    world_id = await _setup_world(
        client,
        spicedb_client,
        officer_id,
        [(c_blue, blue_player, "Party Blue"), (c_gold, gold_player, "Party Gold")],
        "Frontier Sanctum",
    )
    for rel, stype, sid in [("owner", "user", blue_player), ("campaign", "campaign", c_blue)]:
        await spicedb_client.write_relationship("character", char_blue_id, rel, stype, sid)

    # Outsiders are forbidden from reading or mutating the shared world
    h_out = {"x-user-id": outsider}
    assert client.get(f"/api/v1/shared-worlds/{world_id}", headers=h_out).status_code == 403
    fake = {
        "name": "Illegal",
        "coordinates": {"x": 0.0, "y": 0.0},
        "discovered_by_campaign_id": "f",
        "discovered_by_party_name": "F",
    }
    disc_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/discoveries", json=fake, headers=h_out
    )
    assert disc_res.status_code == 403

    # Legitimate party members can access the shared frontier
    for u in (blue_player, gold_player):
        r = client.get(f"/api/v1/shared-worlds/{world_id}", headers={"x-user-id": u})
        assert r.status_code == 200

    # Cross-party Zanzibar scoping: private character sheets remain isolated
    can_view = spicedb_client.check_permission
    assert await can_view("character", char_blue_id, "view", "user", blue_player)
    assert not await can_view("character", char_blue_id, "view", "user", gold_player)
    assert not await can_view("character", char_blue_id, "view", "user", outsider)


@pytest.mark.asyncio
async def test_blackbox_communal_tavern_board_and_notices(
    client: TestClient, spicedb_client: MockSpiceDBClient, party_ids: dict[str, str]
):
    """Test communal tavern notice board for bounties and expedition requests."""
    officer_id = party_ids["officer"]
    blue_player = party_ids["blue_player"]
    gold_player = party_ids["gold_player"]
    c_blue, c_gold = party_ids["campaign_blue"], party_ids["campaign_gold"]

    world_id = await _setup_world(
        client,
        spicedb_client,
        officer_id,
        [(c_blue, blue_player, "Party Blue"), (c_gold, gold_player, "Party Gold")],
        "Frontier Outskirts",
    )

    n_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/tavern-board/notices",
        json={
            "campaign_id": c_blue,
            "author_name": "Laura",
            "title": "Bounty",
            "content": "Trolls",
            "bounty_reward": 150,
        },
        headers={"x-user-id": blue_player},
    )
    assert n_res.status_code == 201
    nid = n_res.json()["notice"]["notice_id"]

    board_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/tavern-board/notices",
        headers={"x-user-id": gold_player},
    )
    assert board_res.status_code == 200
    assert any(n["notice_id"] == nid for n in board_res.json()["notices"])
