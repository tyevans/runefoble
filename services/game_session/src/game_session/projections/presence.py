"""Participant presence and connection state projections."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from game_session.projections.models import ParticipantPresenceModel, PresenceReadModel
from runefoble_events.events import (
    CharacterControlTransferred,
    PlayerJoinedSession,
    PlayerLeftSession,
)
from runefoble_platform.models import utc_now

logger = logging.getLogger("runefoble.game_session.projections.presence")


class PresenceProjection:
    """Projects active players, connection status, and stand-in flags."""

    def __init__(self) -> None:
        self.presence_states: dict[str, PresenceReadModel] = {}

    def _extract_session_id(self, event: Any) -> str:
        if isinstance(event, dict):
            return str(event.get("session_id") or event.get("aggregate_id") or "default")
        return str(
            getattr(event, "session_id", None) or getattr(event, "aggregate_id", None) or "default"
        )

    def apply_event(self, event: Any) -> None:
        """Apply presence events to update participant connection states."""
        session_id = self._extract_session_id(event)
        model = self.presence_states.setdefault(
            session_id, PresenceReadModel(session_id=session_id)
        )
        now_str = utc_now().isoformat()

        if isinstance(event, PlayerJoinedSession):
            model.participants[event.player_id] = ParticipantPresenceModel(
                player_id=event.player_id,
                character_id=str(event.character_id) if event.character_id else None,
                character_name=event.character_name,
                character_class=event.character_class,
                is_present=True,
                is_stand_in_active=False,
                last_seen_at=now_str,
            )
        elif isinstance(event, PlayerLeftSession):
            if event.player_id in model.participants:
                p = model.participants[event.player_id]
                p.is_present = False
                p.is_stand_in_active = True
                p.last_seen_at = now_str
        elif isinstance(event, CharacterControlTransferred):
            if event.player_id in model.participants:
                p = model.participants[event.player_id]
                p.is_present = True
                p.is_stand_in_active = False
                p.character_id = str(event.character_id)
                p.last_seen_at = now_str
        elif isinstance(event, dict):
            self._apply_dict_event(model, event, now_str)

        model.last_updated_at = now_str

    def _apply_dict_event(
        self, model: PresenceReadModel, event: dict[str, Any], now_str: str
    ) -> None:
        etype = event.get("event_type") or event.get("type") or ""
        player_id = str(event.get("player_id", ""))
        if not player_id:
            return

        if "PlayerJoined" in etype or "player.joined" in etype:
            model.participants[player_id] = ParticipantPresenceModel(
                player_id=player_id,
                character_id=str(event.get("character_id", "")) or None,
                character_name=str(event.get("character_name", "")),
                character_class=str(event.get("character_class", "")),
                is_present=True,
                is_stand_in_active=False,
                last_seen_at=now_str,
            )
        elif "PlayerLeft" in etype or "player.left" in etype:
            if player_id in model.participants:
                p = model.participants[player_id]
                p.is_present = False
                p.is_stand_in_active = True
                p.last_seen_at = now_str
        elif (
            "CharacterControlTransferred" in etype or "control.transferred" in etype
        ) and player_id in model.participants:
            p = model.participants[player_id]
            p.is_present = True
            p.is_stand_in_active = False
            p.character_id = str(event.get("character_id", ""))
            p.last_seen_at = now_str

    def get_presence(self, session_id: str | UUID) -> PresenceReadModel | None:
        return self.presence_states.get(str(session_id))

    def get_participants(self, session_id: str | UUID) -> dict[str, ParticipantPresenceModel]:
        p = self.get_presence(session_id)
        return p.participants if p else {}

    def is_player_present(self, session_id: str | UUID, player_id: str) -> bool:
        participants = self.get_participants(session_id)
        return participants.get(
            player_id, ParticipantPresenceModel(player_id=player_id, is_present=False)
        ).is_present

    def get_present_players(self, session_id: str | UUID) -> list[str]:
        return [pid for pid, p in self.get_participants(session_id).items() if p.is_present]


__all__ = ["PresenceProjection"]
