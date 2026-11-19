"""Blackbox tests for mercenary bounty claiming, fulfillment, and escrow release.

Governed by ADR-0001, ADR-0006, ADR-0007, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_SESSION
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.campaign_setup import create_campaign_session, invite_and_join
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.stream_events import assert_stream_events
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.mark.asyncio
async def test_bounty_lifecycle_claim_and_complete_with_escrow(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
) -> None:
    creator_id = "user_questgiver_bram"
    claimant_id = "user_mercenary_rowan"
    claimant_camp = str(uuid4())

    # The creator owns the campaign. The claimant joins as a player through an invite.
    campaign_id, session_id = create_campaign_session(client, creator_id)
    invite_and_join(client, campaign_id, creator_id, claimant_id)

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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(creator_id)}"},
    )
    assert res_post.status_code == 201
    bounty_id = res_post.json()["bounty"]["bounty_id"]

    # 2. Prevent creator from claiming own bounty
    res_self = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={"claimant_campaign_id": claimant_camp, "claimant_party_name": "Self Claim"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(creator_id)}"},
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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(claimant_id)}"},
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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('another_user')}"},
    )
    assert res_double.status_code in (400, 403)

    # 4. Submit proof and complete bounty to disburse escrow
    res_complete = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/complete",
        json={
            "proof": "Delivered 3 sealed vials of basilisk venom to Fort Rowan.",
            "notes": "Verified by Outpost Alchemist.",
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(creator_id)}"},
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
    assert_stream_events(
        mock_bus,
        "runefoble.events.west_marches.mercenary_bounty_posted",
        "runefoble.events.west_marches.mercenary_bounty_claimed",
        "runefoble.events.west_marches.mercenary_bounty_fulfilled",
        stream=STREAM_SESSION,
    )
