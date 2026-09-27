"""Blackbox tests for posting mercenary bounties and querying notice board.

Governed by ADR-0001, ADR-0006, ADR-0007, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_session_stream_events


@pytest.mark.asyncio
async def test_post_bounty_and_query_board(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
) -> None:
    session_id = str(uuid4())
    creator_id = "user_party_leader_alec"

    # Grant session participate permission in SpiceDB
    await spicedb.write_relationship("session", session_id, "participate", "user", creator_id)

    # 1. Post a new mercenary monster hunt bounty
    res_post = client.post(
        f"/sessions/{session_id}/contracts/bounties",
        json={
            "title": "Cull the Glacial Wyrm",
            "description": "A frost wyrm is terrorizing the mountain pass.",
            "target_type": "monster_hunt",
            "target_name": "Glacial Wyrm",
            "target_quantity": 1,
            "escrow_gold": 450,
            "escrow_items": [{"item_id": "frost_gem", "quantity": 2}],
            "campaign_id": str(uuid4()),
        },
        headers={"x-user-id": creator_id},
    )
    assert res_post.status_code == 201, res_post.text
    body = res_post.json()
    bounty = body["bounty"]
    bounty_id = bounty["bounty_id"]

    assert bounty["title"] == "Cull the Glacial Wyrm"
    assert bounty["status"] == "POSTED"
    assert bounty["escrow_locked"] is True
    assert bounty["escrow_gold"] == 450
    assert len(bounty["escrow_items"]) == 1
    assert bounty["poster_user_id"] == creator_id

    # Verify event published to Redis Streams
    assert_session_stream_events(mock_bus, "MercenaryBountyPosted")

    # 2. Query open notice board
    res_list = client.get(
        f"/sessions/{session_id}/contracts/bounties",
        headers={"x-user-id": creator_id},
    )
    assert res_list.status_code == 200
    bounties = res_list.json()["bounties"]
    assert len(bounties) == 1
    assert bounties[0]["bounty_id"] == bounty_id

    # 3. Test filtering by target_type
    res_filtered = client.get(
        f"/sessions/{session_id}/contracts/bounties?target_type=monster_hunt",
        headers={"x-user-id": creator_id},
    )
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()["bounties"]) == 1

    res_empty_type = client.get(
        f"/sessions/{session_id}/contracts/bounties?target_type=resource_retrieval",
        headers={"x-user-id": creator_id},
    )
    assert res_empty_type.status_code == 200
    assert len(res_empty_type.json()["bounties"]) == 0

    # 4. Test filtering by min_gold
    res_gold = client.get(
        f"/sessions/{session_id}/contracts/bounties?min_gold=400",
        headers={"x-user-id": creator_id},
    )
    assert len(res_gold.json()["bounties"]) == 1

    res_gold_high = client.get(
        f"/sessions/{session_id}/contracts/bounties?min_gold=500",
        headers={"x-user-id": creator_id},
    )
    assert len(res_gold_high.json()["bounties"]) == 0

    # 5. Get individual bounty by ID
    res_get = client.get(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}",
        headers={"x-user-id": creator_id},
    )
    assert res_get.status_code == 200
    assert res_get.json()["bounty"]["bounty_id"] == bounty_id
