"""Invite token generation, lifecycle management, and redemption."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from gateway_api.campaign_store.models import InviteRecord, InviteTokenRecord
from gateway_api.models import InviteResponse, JoinCampaignResponse


def generate_invite_token(nbytes: int = 16) -> str:
    """Generate a cryptographically secure URL-safe invite token."""
    return secrets.token_urlsafe(nbytes)


def calculate_invite_expiry(expires_in_hours: int | None = 72) -> datetime | None:
    """Calculate expiration timestamp for an invite token."""
    return datetime.now(UTC) + timedelta(hours=expires_in_hours) if expires_in_hours else None


def format_invite_response(inv: InviteRecord) -> InviteResponse:
    """Format an InviteRecord into an API InviteResponse."""
    data = inv.to_dict()
    data.pop("created_by", None)
    return InviteResponse(**data, invite_url=f"/#/join/{inv.token}")


class InviteManager:
    """Manages storage, validation, and usage tracking for invite tokens."""

    def __init__(self) -> None:
        self._invites: dict[str, InviteTokenRecord] = {}

    def create_invite(
        self,
        campaign_id: str,
        role: str,
        created_by: str,
        expires_in_hours: int | None = 72,
        max_uses: int | None = None,
    ) -> InviteTokenRecord:
        rec = InviteTokenRecord(
            token=generate_invite_token(),
            campaign_id=campaign_id,
            role=role,
            created_by=created_by,
            expires_at=calculate_invite_expiry(expires_in_hours),
            max_uses=max_uses,
        )
        self._invites[rec.token] = rec
        return rec

    def get_invite(self, token: str) -> InviteTokenRecord | None:
        return self._invites.get(token)

    def use_invite(self, token: str) -> tuple[InviteTokenRecord | None, str | None]:
        if not (rec := self._invites.get(token)):
            return None, "Invalid invite token"
        is_valid, err = rec.validate_usability()
        if not is_valid:
            return None, err
        rec.uses += 1
        return rec, None

    def reset(self) -> None:
        self._invites.clear()


async def join_from_invite(
    token: str, user_id: str, client: Any, store: Any = None
) -> JoinCampaignResponse:
    """Validate invite token and register user in SpiceDB."""
    if store is None:
        from gateway_api.campaign_store.store import campaign_store

        store = campaign_store

    inv, err = store.use_invite(token)
    if err or not inv:
        detail = {"error": "invalid_invite", "message": err or "Invalid invite token"}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    rel = "spectator" if inv.role == "spectator" else "player"
    await client.write_relationship("campaign", inv.campaign_id, rel, "user", user_id)
    return JoinCampaignResponse(
        status="joined",
        campaign_id=inv.campaign_id,
        user_id=user_id,
        role=inv.role,
        zanzibar_relation=f"campaign:{inv.campaign_id}#{rel}@user:{user_id}",
    )
