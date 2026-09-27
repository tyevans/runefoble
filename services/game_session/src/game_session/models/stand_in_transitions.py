"""Presence and stand-in state transitions mixin for GameSessionState."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from game_session.models.session import GameSessionState


class StandInTransitionsMixin:
    """Transition methods for player presence, stand-in actions, and control transfer."""

    def without_player_presence(self: GameSessionState, player_id: str) -> GameSessionState:
        participants = dict(self.participants)
        if player_id in participants:
            p = participants[player_id]
            participants[player_id] = p.model_copy(
                update={"is_present": False, "is_stand_in_active": True}
            )
        return self.model_copy(update={"participants": participants})

    def with_character_control_transferred(
        self: GameSessionState, player_id: str, character_id: UUID
    ) -> GameSessionState:
        participants = dict(self.participants)
        if player_id in participants:
            p = participants[player_id]
            participants[player_id] = p.model_copy(
                update={"is_present": True, "is_stand_in_active": False}
            )
        else:
            for pid, p in list(participants.items()):
                if p.character_id == character_id:
                    participants[pid] = p.model_copy(
                        update={
                            "is_present": True,
                            "is_stand_in_active": False,
                            "player_id": player_id,
                        }
                    )
                    break
        return self.model_copy(update={"participants": participants})

    def with_stand_in_event(self: GameSessionState, event: Any) -> GameSessionState:
        return self.with_stand_in_action(
            {
                "character_name": event.character_name,
                "action_type": event.action_type,
                "dialogue": event.dialogue,
                "penalties_applied": event.penalties_applied,
                "flavor_text": event.flavor_text,
            }
        )

    def with_stand_in_action(self: GameSessionState, action: dict[str, Any]) -> GameSessionState:
        actions = list(self.stand_in_actions)
        actions.append(action)
        return self.model_copy(update={"stand_in_actions": actions})
