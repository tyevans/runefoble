"""Domain and API models for mercenary bounty contracts and escrow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BountyStatus:
    POSTED = "POSTED"
    ACCEPTED = "ACCEPTED"
    FULFILLED = "FULFILLED"
    DISPUTED = "DISPUTED"
    COMPLETED = "COMPLETED"


class MercenaryBountyState(BaseModel):
    """Event-sourced state of a mercenary bounty contract."""

    bounty_id: str = ""
    session_id: str = ""
    campaign_id: str = ""
    title: str = ""
    description: str = ""
    target_type: str = "monster_hunt"
    target_name: str = ""
    target_quantity: int = 1
    escrow_gold: int = 0
    escrow_items: list[dict[str, Any]] = Field(default_factory=list)
    poster_user_id: str | None = None
    claimant_user_id: str | None = None
    claimant_campaign_id: str = ""
    claimant_party_name: str = ""
    status: str = BountyStatus.POSTED
    escrow_locked: bool = True
    proof: str = ""
    disputed_reason: str = ""
    disbursed_to: str = ""
    payout: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class PostBountyRequest(BaseModel):
    """Payload to post an in-world mercenary bounty with escrow."""

    title: str
    description: str = ""
    target_type: str = "monster_hunt"
    target_name: str
    target_quantity: int = 1
    escrow_gold: int = 0
    escrow_items: list[dict[str, Any]] = Field(default_factory=list)
    campaign_id: str = ""


class ClaimBountyRequest(BaseModel):
    """Payload to claim an open bounty contract."""

    claimant_campaign_id: str = ""
    claimant_party_name: str = ""


class CompleteBountyRequest(BaseModel):
    """Payload to submit proof and disburse escrow."""

    proof: str = ""
    notes: str = ""


class DisputeBountyRequest(BaseModel):
    """Payload to dispute fulfillment proof."""

    reason: str
