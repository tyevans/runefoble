"""Campaign session models and in-memory session manager."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from gateway_api.models import CampaignSessionResponse


@dataclass
class CampaignSessionRecord:
    id: str
    campaign_id: str
    title: str
    status: str = "lobby"
    round: int = 1
    participants_count: int = 0
    scheduled_at: str | None = None
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_response(self) -> CampaignSessionResponse:
        return CampaignSessionResponse(
            id=self.id,
            campaign_id=self.campaign_id,
            title=self.title,
            status=self.status,
            round=self.round,
            participants_count=self.participants_count,
            scheduled_at=self.scheduled_at,
            created_at=self.created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "campaignId": self.campaign_id,
            "title": self.title,
            "status": self.status,
            "round": self.round,
            "participants_count": self.participants_count,
            "participantsCount": self.participants_count,
            "scheduled_at": self.scheduled_at,
            "description": self.description,
            "created_at": self.created_at,
        }


class SessionManager:
    """Manages active, lobby, and scheduled sessions for campaigns."""

    def __init__(self) -> None:
        self._campaign_sessions: dict[str, list[CampaignSessionRecord]] = {}

    def create_session(
        self,
        campaign_id: str,
        title: str,
        status: str = "lobby",
        scheduled_at: str | None = None,
        description: str = "",
        session_id: str | None = None,
    ) -> CampaignSessionRecord:
        sid = session_id or f"session-{uuid.uuid4().hex[:8]}"
        rec = CampaignSessionRecord(
            id=sid,
            campaign_id=campaign_id,
            title=title,
            status=status,
            scheduled_at=scheduled_at,
            description=description,
        )
        if campaign_id not in self._campaign_sessions:
            self._campaign_sessions[campaign_id] = []
        self._campaign_sessions[campaign_id].append(rec)
        return rec

    def get_campaign_sessions(self, campaign_id: str) -> list[CampaignSessionRecord]:
        return list(self._campaign_sessions.get(campaign_id, []))

    def get_session(self, session_id: str) -> CampaignSessionRecord | None:
        for sessions in self._campaign_sessions.values():
            for s in sessions:
                if s.id == session_id:
                    return s
        return None

    def reset(self) -> None:
        self._campaign_sessions.clear()
