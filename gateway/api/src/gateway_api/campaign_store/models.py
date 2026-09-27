"""Record models and default participants for campaign store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from gateway_api.models import CampaignSummaryResponse


@dataclass
class CampaignRecord:
    id: str
    title: str
    description: str = ""
    setting: str = ""
    system: str = "5e"
    status: str = "active"
    owner_id: str = ""
    cover_image_url: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_summary(self, role: str | None = None, member_count: int = 1) -> CampaignSummaryResponse:
        data = self.to_dict()
        data.pop("campaign_id", None)
        return CampaignSummaryResponse(**data, role=role, member_count=member_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "campaign_id": self.id,
            "title": self.title,
            "description": self.description,
            "setting": self.setting,
            "system": self.system,
            "status": self.status,
            "owner_id": self.owner_id,
            "cover_image_url": self.cover_image_url,
            "settings": self.settings,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class CampaignMemberRecord:
    user_id: str
    campaign_id: str
    role: str
    subject_type: str = "user"
    joined_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "campaign_id": self.campaign_id,
            "role": self.role,
            "subject_type": self.subject_type,
            "joined_at": self.joined_at,
        }


@dataclass
class InviteTokenRecord:
    token: str
    campaign_id: str
    role: str
    created_by: str
    expires_at: datetime | None = None
    max_uses: int | None = None
    uses: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def validate_usability(self) -> tuple[bool, str | None]:
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False, "Invite token has expired"
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False, "Invite token usage limit reached"
        return True, None

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "campaign_id": self.campaign_id,
            "role": self.role,
            "created_by": self.created_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "max_uses": self.max_uses,
            "uses": self.uses,
            "created_at": self.created_at.isoformat(),
        }


InviteRecord = InviteTokenRecord

DEFAULT_SESSION_PARTICIPANTS = [
    {"username": "Alice", "character": "Valeros", "role": "player", "online": True},
    {
        "username": "Bob",
        "character": "Kyra",
        "role": "player",
        "online": False,
        "ai_stand_in": True,
    },
]

DEFAULT_BOARD_TOKENS = [
    {"id": "t1", "name": "Valeros", "x": 2, "y": 3, "color": "#2563eb"},
    {"id": "t2", "name": "Kyra", "x": 3, "y": 3, "color": "#db2777", "is_ai_controlled": True},
]
