"""Blackbox tests for contract lifecycle domain engine transitions and dispute flows.

Governed by ADR-0007, Hard Invariant 2, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

from game_session.contracts.engine import MercenaryBountyAggregate
from game_session.contracts.models import BountyStatus


def test_aggregate_lifecycle_transitions_and_dispute_flow() -> None:
    """Test full aggregate lifecycle through domain engine frontdoor."""
    bounty_id = uuid4()
    session_id = str(uuid4())
    campaign_id = str(uuid4())
    agg = MercenaryBountyAggregate(bounty_id)

    # 1. Post bounty -> POSTED with locked escrow
    agg.post_bounty(
        session_id=session_id,
        campaign_id=campaign_id,
        title="Retrieve the Starforged Ore",
        target_type="resource_retrieval",
        target_name="Starforged Ore",
        target_quantity=5,
        escrow_gold=800,
        escrow_items=[{"item_id": "star_shard", "quantity": 1}],
        poster_user_id="user_bram",
    )
    assert agg.state.status == BountyStatus.POSTED
    assert agg.state.escrow_locked is True
    assert agg.state.escrow_gold == 800

    # 2. Claim bounty -> ACCEPTED
    agg.claim_bounty(
        uid="user_claimant",
        campaign_id=str(uuid4()),
        party_name="Nightshades",
    )
    assert agg.state.status == BountyStatus.ACCEPTED
    assert agg.state.claimant_user_id == "user_claimant"
    assert agg.state.escrow_locked is True

    # 3. Fulfill bounty -> FULFILLED
    agg.fulfill_bounty(
        proof="Delivered 5 chunks of meteoric ore",
        fulfilled_by="user_claimant",
    )
    assert agg.state.status == BountyStatus.FULFILLED
    assert agg.state.proof == "Delivered 5 chunks of meteoric ore"
    assert agg.state.escrow_locked is True

    # 4. Dispute bounty -> DISPUTED (escrow remains locked)
    agg.dispute_bounty(
        reason="Only 4 chunks verified to be authentic ore",
        disputed_by="user_bram",
    )
    assert agg.state.status == BountyStatus.DISPUTED
    assert agg.state.disputed_reason == "Only 4 chunks verified to be authentic ore"
    assert agg.state.escrow_locked is True

    # 5. Resolve and Complete bounty -> COMPLETED (escrow unlocked, payout disbursed)
    payout = agg.complete_bounty(
        proof="Fifth chunk verified and accepted by smith",
        disbursed_by="user_bram",
    )
    assert agg.state.status == BountyStatus.COMPLETED
    assert agg.state.escrow_locked is False
    assert payout["gold"] == 800
    assert len(payout["items"]) == 1
    assert agg.state.disbursed_to == "user_claimant"
