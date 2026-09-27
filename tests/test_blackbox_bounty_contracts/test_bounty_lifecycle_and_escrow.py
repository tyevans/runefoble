"""Blackbox tests for mercenary bounty claiming, fulfillment, and escrow release.

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
async def test_bounty_lifecycle_claim_and_complete_with_escrow(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
) -> None:
    session_id = str(uuid4())
    creator_id = "user_questgiver_bram"
    claimant_id = "user_mercenary_rowan"
    claimant_camp = str(uuid4())

    await spicedb.write_relationship("session", session_id, "participate", "user", creator_id)
    await spicedb.write_relationship("session", session_id, "participate", "user", claimant_id)

    # 1. Post bounty with 600 gold and healing elixir in escrow
    res_post = client.post(
        f"/sessions/{session_id}/contracts/bounties",
        json={
            "title": "Harvest Basilisk Venom",
            "description": "Retrieve 3 vials of fresh venom from the Petrified Vale.",
            "target_type": "resource_retrieval",
            "target_name": "Basilisk Venom",
            "target_quantity": 3,
            "escrow_gold": 600,
            "escrow_items": [{"item_id": "greater_healing_potion", "quantity": 1}],
        },
        headers={"x-user-id": creator_id},
    )
    assert res_post.status_code == 201
    bounty_id = res_post.json()["bounty"]["bounty_id"]

    # 2. Prevent creator from claiming own bounty
    res_self = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={"claimant_campaign_id": claimant_camp, "claimant_party_name": "Self Claim"},
        headers={"x-user-id": creator_id},
    )
    assert res_self.status_code == 400
    assert "Creator cannot claim" in res_self.json()["detail"]

    # 3. Claimant claims bounty
    res_claim = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={
            "claimant_campaign_id": claimant_camp,
            "claimant_party_name": "The Emerald Vanguard",
        },
        headers={"x-user-id": claimant_id},
    )
    assert res_claim.status_code == 200
    claimed_bounty = res_claim.json()["bounty"]
    assert claimed_bounty["status"] == "ACCEPTED"
    assert claimed_bounty["claimant_user_id"] == claimant_id
    assert claimed_bounty["claimant_party_name"] == "The Emerald Vanguard"
    assert claimed_bounty["escrow_locked"] is True

    # Cannot claim again
    res_double = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={"claimant_campaign_id": claimant_camp, "claimant_party_name": "Other Party"},
        headers={"x-user-id": "another_user"},
    )
    assert res_double.status_code in (400, 403)

    # 4. Submit proof and complete bounty to disburse escrow
    res_complete = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/complete",
        json={
            "proof": "Delivered 3 sealed vials of basilisk venom to Fort Rowan.",
            "notes": "Verified by Outpost Alchemist.",
        },
        headers={"x-user-id": creator_id},
    )
    assert res_complete.status_code == 200
    comp_body = res_complete.json()

    assert comp_body["status"] == "COMPLETED"
    assert comp_body["escrow_locked"] is False
    assert comp_body["payout"]["gold"] == 600
    assert len(comp_body["payout"]["items"]) == 1
    assert comp_body["payout"]["items"][0]["item_id"] == "greater_healing_potion"

    final_bounty = comp_body["bounty"]
    assert final_bounty["status"] == "COMPLETED"
    assert final_bounty["escrow_locked"] is False
    assert final_bounty["proof"] == "Delivered 3 sealed vials of basilisk venom to Fort Rowan."
    assert final_bounty["disbursed_to"] == claimant_id

    # Verify event stream
    assert_session_stream_events(
        mock_bus,
        "MercenaryBountyPosted",
        "MercenaryBountyClaimed",
        "MercenaryBountyFulfilled",
    )
