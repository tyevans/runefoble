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
        self._campaign_sessions: dict[str, list[CampaignSessionRecord]] = {
            "4": [
                CampaignSessionRecord(
                    id="14",
                    campaign_id="4",
                    title="Session #14: Tomb of the Star-Eater",
                    status="active",
                    round=3,
                    participants_count=4,
                ),
                CampaignSessionRecord(
                    id="15",
                    campaign_id="4",
                    title="Session #15: Chamber of Horrors",
                    status="lobby",
                    round=1,
                    participants_count=3,
                ),
            ],
        }

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
        self.__init__()


DEFAULT_SESSION_PARTICIPANTS: list[dict[str, Any]] = [
    {
        "userId": "user-valeros",
        "username": "Valeros",
        "role": "player",
        "character": "Valeros",
        "characterId": "char-valeros",
        "characterName": "Valeros",
        "characterClass": "Fighter",
        "characterLevel": 4,
        "isReady": False,
        "isAbsent": False,
        "onlineStatus": "online",
        "online": True,
        "ai_stand_in": False,
    },
    {
        "userId": "user-sarah",
        "username": "Sarah",
        "role": "player",
        "character": "Sarah",
        "characterId": "char-sarah",
        "characterName": "Sarah",
        "characterClass": "Rogue",
        "characterLevel": 3,
        "isReady": False,
        "isAbsent": False,
        "onlineStatus": "online",
        "online": True,
        "ai_stand_in": False,
    },
    {
        "userId": "user-kyra",
        "username": "Kyra",
        "role": "player",
        "character": "Kyra",
        "characterId": "char-kyra",
        "characterName": "Kyra",
        "characterClass": "Cleric",
        "characterLevel": 4,
        "isReady": False,
        "isAbsent": False,
        "onlineStatus": "offline",
        "online": False,
        "ai_stand_in": False,
    },
]

DEFAULT_BOARD_TOKENS: list[dict[str, Any]] = [
    {"id": "t1", "name": "Valeros", "x": 2, "y": 2, "color": "#2563eb"},
    {"id": "t2", "name": "Kyra", "x": 3, "y": 3, "color": "#db2777", "is_ai_controlled": True},
]
