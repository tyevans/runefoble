"""Domain events for frontier mercenary bounties and retrieval contracts."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class MercenaryBountyPostedEvent(BaseRunefobleEvent):
    """Fired when a new mercenary bounty or retrieval contract is posted."""

    aggregate_type: str = "MercenaryBounty"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "MercenaryBountyPosted"
    bounty_id: str = ""
    session_id: UUID | str | None = None
    campaign_id: UUID | str | None = None
    title: str = ""
    description: str = ""
    target_type: str = "monster_hunt"
    target_name: str = ""
    target_quantity: int = 1
    escrow_gold: int = 0
    escrow_items: list[dict[str, Any]] = Field(default_factory=list)
    poster_user_id: str | None = None
    created_at: str | None = None


@register_event
class MercenaryBountyClaimedEvent(BaseRunefobleEvent):
    """Fired when an adventuring party claims an active mercenary bounty."""

    aggregate_type: str = "MercenaryBounty"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "MercenaryBountyClaimed"
    bounty_id: str = ""
    session_id: UUID | str | None = None
    claimant_user_id: str = ""
    claimant_campaign_id: str = ""
    claimant_party_name: str = ""
    claimed_at: str | None = None


@register_event
class MercenaryBountyFulfilledEvent(BaseRunefobleEvent):
    """Fired when proof of bounty fulfillment is submitted or completed."""

    aggregate_type: str = "MercenaryBounty"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "MercenaryBountyFulfilled"
    bounty_id: str = ""
    session_id: UUID | str | None = None
    proof: str = ""
    status: str = "FULFILLED"
    payout_gold: int = 0
    payout_items: list[dict[str, Any]] = Field(default_factory=list)
    fulfilled_by: str = ""
    fulfilled_at: str | None = None


MercenaryBountyPosted = MercenaryBountyPostedEvent
MercenaryBountyClaimed = MercenaryBountyClaimedEvent
MercenaryBountyFulfilled = MercenaryBountyFulfilledEvent

__all__ = [
    "MercenaryBountyClaimed",
    "MercenaryBountyClaimedEvent",
    "MercenaryBountyFulfilled",
    "MercenaryBountyFulfilledEvent",
    "MercenaryBountyPosted",
    "MercenaryBountyPostedEvent",
]
