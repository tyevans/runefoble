"""Campaign invite aggregate: one stream per invite, keyed by a hash of the token.

The raw token is never stored. The stream ID is derived from SHA-256 of the token, so a
redeemer can find the invite from the token alone, with no index that could be lost on restart.
Governed by ADR-0011 and ADR-0015 decision (a).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.campaign.errors import InviteExhaustedError, InviteExpiredError
from pydantic import BaseModel, Field
from runefoble_events.events import (
    CampaignInviteCreated,
    CampaignInviteRedeemed,
    PendingJoinCompleted,
    PendingJoinRecorded,
)

INVITE_TOKEN_BYTES = 16


class InviteState(BaseModel):
    campaign_id: str = ""
    role: str = "player"
    created_by: str = ""
    expires_at: datetime | None = None
    max_uses: int | None = None
    uses: int = 0
    # Identity provider user id -> role, for each account that this invite created and that has
    # not yet signed in to join (ADR-0023 d, e).
    pending: dict[str, str] = Field(default_factory=dict)


def generate_invite_token() -> str:
    """Return a new URL-safe invite token from the system CSPRNG."""
    return secrets.token_urlsafe(INVITE_TOKEN_BYTES)


def invite_stream_id(token: str) -> UUID:
    """Derive the invite aggregate ID from the token. The token itself is not stored."""
    return UUID(bytes=hashlib.sha256(token.encode("utf-8")).digest()[:16])


class InviteAggregate(DeclarativeAggregate[InviteState]):
    """Issues an invite and checks expiry and use count on redemption."""

    aggregate_type = "CampaignInvite"
    requires_creation_event = True

    def issue(
        self,
        *,
        campaign_id: UUID,
        role: str,
        created_by: str,
        expires_at: datetime | None,
        max_uses: int | None,
    ) -> None:
        if self.is_created:
            raise ValueError("Invite already exists")
        self.create_event(
            CampaignInviteCreated,
            campaign_id=campaign_id,
            role=role,
            created_by=created_by,
            expires_at=expires_at,
            max_uses=max_uses,
        )

    def ensure_redeemable(self, now: datetime) -> None:
        """Raise when the invite has expired or has no uses left. Records nothing."""
        state = self.state
        if state.expires_at is not None and now > state.expires_at:
            raise InviteExpiredError("Invite token has expired")
        if state.max_uses is not None and state.uses >= state.max_uses:
            raise InviteExhaustedError("Invite token usage limit reached")

    def redeem(self, user_id: str, now: datetime) -> None:
        """Record one use. Raise when the invite has expired or has no uses left."""
        self.ensure_redeemable(now)
        self.create_event(
            CampaignInviteRedeemed,
            campaign_id=UUID(self.state.campaign_id),
            user_id=user_id,
        )

    def pending_role_of(self, user_id: str) -> str | None:
        return self.state.pending.get(user_id)

    def record_pending(self, user_id: str, role: str) -> None:
        """Hold the join of an account that this invite created, until it signs in."""
        self.create_event(
            PendingJoinRecorded,
            campaign_id=self.state.campaign_id,
            user_id=user_id,
            role=role,
        )

    def complete_pending(self, user_id: str) -> None:
        """Clear the pending join of `user_id`. The use was already counted when it was made."""
        if self.pending_role_of(user_id) is None:
            raise ValueError("No pending join exists for this user")
        self.create_event(
            PendingJoinCompleted,
            campaign_id=self.state.campaign_id,
            user_id=user_id,
        )

    @handles(CampaignInviteCreated)
    def _on_created(self, event: CampaignInviteCreated) -> None:
        self._state = InviteState(
            campaign_id=str(event.campaign_id),
            role=event.role,
            created_by=event.created_by,
            expires_at=event.expires_at,
            max_uses=event.max_uses,
        )

    @handles(CampaignInviteRedeemed)
    def _on_redeemed(self, event: CampaignInviteRedeemed) -> None:
        self.state.uses += 1

    @handles(PendingJoinRecorded)
    def _on_pending_recorded(self, event: PendingJoinRecorded) -> None:
        self.state.pending[event.user_id] = event.role

    @handles(PendingJoinCompleted)
    def _on_pending_completed(self, event: PendingJoinCompleted) -> None:
        self.state.pending.pop(event.user_id, None)


def invite_expiry(expires_in_hours: int | None, now: datetime) -> datetime | None:
    """Return the expiry instant, or None when the invite never expires."""
    if expires_in_hours is None:
        return None
    return now + timedelta(hours=expires_in_hours)
