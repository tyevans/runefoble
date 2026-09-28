"""In-memory campaign metadata store and lifecycle repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from gateway_api.campaign_store.invites import InviteManager
from gateway_api.campaign_store.models import CampaignRecord, CampaignSessionRecord, InviteRecord
from gateway_api.campaign_store.queries import (
    build_campaign_summary,
    get_all_viewable_campaigns,
    get_campaign_members,
    get_user_campaign_role,
)
from gateway_api.campaign_store.sessions import SessionManager


class CampaignStore:
    """Thread-safe in-memory store for campaigns, sessions, and invites."""

    def __init__(
        self,
        invite_manager: InviteManager | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        self._campaigns: dict[str, CampaignRecord] = {}
        self._invite_manager = invite_manager or InviteManager()
        self._session_manager = session_manager or SessionManager()

    @property
    def _invites(self) -> dict[str, InviteRecord]:
        return self._invite_manager._invites

    @property
    def _campaign_sessions(self) -> dict[str, list[CampaignSessionRecord]]:
        return self._session_manager._campaign_sessions

    def create_campaign(
        self,
        campaign_id: str,
        title: str,
        owner_id: str,
        description: str = "",
        setting: str = "",
        system: str = "5e",
        cover_image_url: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> CampaignRecord:
        rec = CampaignRecord(
            id=campaign_id,
            title=title,
            description=description,
            setting=setting,
            system=system,
            owner_id=owner_id,
            cover_image_url=cover_image_url,
            settings=settings or {},
        )
        self._campaigns[campaign_id] = rec
        return rec

    def get_campaign(self, campaign_id: str) -> CampaignRecord | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(self) -> list[CampaignRecord]:
        return list(self._campaigns.values())

    def update_campaign(self, campaign_id: str, **kwargs: Any) -> CampaignRecord | None:
        rec = self._campaigns.get(campaign_id)
        if not rec:
            return None
        valid = {
            "title",
            "description",
            "setting",
            "system",
            "cover_image_url",
            "status",
            "settings",
        }
        for k, v in kwargs.items():
            if k in valid and v is not None:
                setattr(rec, k, v)
        rec.updated_at = datetime.now(UTC).isoformat()
        return rec

    def create_from_request(self, req: Any, owner_id: str) -> tuple[str, CampaignRecord]:
        cid = f"camp-{uuid.uuid4().hex[:8]}"
        rec = self.create_campaign(
            cid,
            req.title,
            owner_id,
            req.description,
            req.setting,
            req.system,
            req.cover_image_url,
            req.settings,
        )
        return cid, rec

    def update_from_request(self, campaign_id: str, req: Any, owner_id: str) -> CampaignRecord:
        if not self.get_campaign(campaign_id):
            self.create_campaign(campaign_id, req.title or f"Campaign {campaign_id}", owner_id)
        return (
            self.update_campaign(
                campaign_id,
                title=req.title,
                description=req.description,
                setting=req.setting,
                system=req.system,
                cover_image_url=req.cover_image_url,
                status=req.status,
                settings=req.settings,
            )
            or self._campaigns[campaign_id]
        )

    def create_invite(self, *args: Any, **kwargs: Any) -> InviteRecord:
        return self._invite_manager.create_invite(*args, **kwargs)

    def get_invite(self, token: str) -> InviteRecord | None:
        return self._invite_manager.get_invite(token)

    def use_invite(self, token: str) -> tuple[InviteRecord | None, str | None]:
        return self._invite_manager.use_invite(token)

    def create_session(self, *args: Any, **kwargs: Any) -> CampaignSessionRecord:
        return self._session_manager.create_session(*args, **kwargs)

    def get_campaign_sessions(self, campaign_id: str) -> list[CampaignSessionRecord]:
        return self._session_manager.get_campaign_sessions(campaign_id)

    def get_session(self, session_id: str) -> CampaignSessionRecord | None:
        return self._session_manager.get_session(session_id)

    def reset(self) -> None:
        self._campaigns.clear()
        self._session_manager.reset()
        self._invite_manager.reset()


campaign_store = CampaignStore()

__all__ = [
    "CampaignStore",
    "build_campaign_summary",
    "campaign_store",
    "get_all_viewable_campaigns",
    "get_campaign_members",
    "get_user_campaign_role",
]
