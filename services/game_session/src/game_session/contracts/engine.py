"""Domain engine for mercenary bounty contracts and escrow locks.

Governed by ADR-0001, ADR-0006, ADR-0007, and Hard Invariants 2 and 6.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.contracts.models import BountyStatus, MercenaryBountyState
from runefoble_events.contracts import (
    MercenaryBountyClaimedEvent,
    MercenaryBountyFulfilledEvent,
    MercenaryBountyPostedEvent,
)

_COMPLETABLE = (BountyStatus.ACCEPTED, BountyStatus.FULFILLED, BountyStatus.DISPUTED)


def _to_u(val: Any) -> UUID:
    return val if isinstance(val, UUID) else UUID(str(val))


def _now() -> str:
    return datetime.now(UTC).isoformat()


class MercenaryBountyAggregate(DeclarativeAggregate[MercenaryBountyState]):
    """Aggregate managing contract transitions: POSTED, ACCEPTED, FULFILLED, DISPUTED, COMPLETED."""

    aggregate_type = "MercenaryBounty"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kw: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kw)
        if self._state is None:
            self._state = MercenaryBountyState(bounty_id=str(aggregate_id or ""))

    @handles(MercenaryBountyPostedEvent)
    def handle_posted(self, ev: MercenaryBountyPostedEvent) -> None:
        d = ev.model_dump()
        fields = MercenaryBountyState.model_fields
        payload = {k: v for k, v in d.items() if k in fields and v is not None}
        payload["session_id"] = str(ev.session_id or "")
        payload["campaign_id"] = str(ev.campaign_id or "")
        payload["bounty_id"] = str(ev.bounty_id or ev.aggregate_id)
        self._state = MercenaryBountyState(
            **payload, status=BountyStatus.POSTED, escrow_locked=True
        )

    @handles(MercenaryBountyClaimedEvent)
    def handle_claimed(self, ev: MercenaryBountyClaimedEvent) -> None:
        self.state.status = BountyStatus.ACCEPTED
        self.state.claimant_user_id = ev.claimant_user_id
        self.state.claimant_campaign_id = ev.claimant_campaign_id
        self.state.claimant_party_name = ev.claimant_party_name

    @handles(MercenaryBountyFulfilledEvent)
    def handle_fulfilled(self, ev: MercenaryBountyFulfilledEvent) -> None:
        self.state.status = ev.status
        if ev.proof:
            self.state.proof = ev.proof
        if ev.status == BountyStatus.DISPUTED:
            self.state.disputed_reason = ev.proof or "Fulfillment disputed"
        elif ev.status == BountyStatus.COMPLETED:
            self.state.escrow_locked = False
            self.state.disbursed_to = ev.fulfilled_by
            self.state.payout = {"gold": ev.payout_gold, "items": list(ev.payout_items)}

    def post_bounty(self, session_id: str, campaign_id: str, **kw: Any) -> str:
        bid = str(self.aggregate_id or uuid4())
        sid = _to_u(session_id) if session_id else None
        cid = _to_u(campaign_id) if campaign_id else None
        self.create_event(
            MercenaryBountyPostedEvent,
            aggregate_id=_to_u(bid),
            bounty_id=bid,
            session_id=sid,
            campaign_id=cid,
            created_at=_now(),
            **kw,
        )
        return bid

    def claim_bounty(self, uid: str, campaign_id: str = "", party_name: str = "") -> None:
        if self.state.status != BountyStatus.POSTED:
            raise ValueError(f"Bounty cannot be claimed in status '{self.state.status}'")
        if self.state.poster_user_id and self.state.poster_user_id == uid:
            raise ValueError("Creator cannot claim their own bounty")
        self.create_event(
            MercenaryBountyClaimedEvent,
            aggregate_id=_to_u(self.state.bounty_id or self.aggregate_id),
            bounty_id=self.state.bounty_id,
            session_id=self.state.session_id or None,
            claimant_user_id=uid,
            claimant_campaign_id=campaign_id,
            claimant_party_name=party_name,
            claimed_at=_now(),
        )

    def _emit(
        self, status: str, proof: str, user: str, g: int = 0, items: list[Any] | None = None
    ) -> None:
        self.create_event(
            MercenaryBountyFulfilledEvent,
            aggregate_id=_to_u(self.state.bounty_id or self.aggregate_id),
            bounty_id=self.state.bounty_id,
            session_id=self.state.session_id or None,
            proof=proof,
            status=status,
            payout_gold=g,
            payout_items=items or [],
            fulfilled_by=user,
            fulfilled_at=_now(),
        )

    def fulfill_bounty(self, proof: str, fulfilled_by: str) -> None:
        if self.state.status not in (BountyStatus.ACCEPTED, BountyStatus.DISPUTED):
            raise ValueError(f"Cannot fulfill bounty in status '{self.state.status}'")
        self._emit(BountyStatus.FULFILLED, proof, fulfilled_by)

    def dispute_bounty(self, reason: str, disputed_by: str) -> None:
        if self.state.status not in (BountyStatus.ACCEPTED, BountyStatus.FULFILLED):
            raise ValueError(f"Cannot dispute bounty in status '{self.state.status}'")
        self._emit(BountyStatus.DISPUTED, reason, disputed_by)

    def complete_bounty(self, proof: str = "", disbursed_by: str = "") -> dict[str, Any]:
        if self.state.status not in _COMPLETABLE:
            raise ValueError(f"Cannot complete bounty in status '{self.state.status}'")
        dest = self.state.claimant_user_id or disbursed_by
        g, items = self.state.escrow_gold, list(self.state.escrow_items)
        self._emit(BountyStatus.COMPLETED, proof or self.state.proof, dest, g, items)
        return {"gold": g, "items": items}
