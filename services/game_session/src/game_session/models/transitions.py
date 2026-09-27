"""State transition and mutation helper mixin for GameSessionState."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from game_session.models.combat_transitions import CombatTransitionsMixin
from game_session.models.reaction_transitions import ReactionTransitionsMixin
from game_session.models.stand_in_transitions import StandInTransitionsMixin

if TYPE_CHECKING:
    from game_session.models.session import GameSessionState, ParticipantState


class GameSessionTransitionsMixin(
    CombatTransitionsMixin,
    ReactionTransitionsMixin,
    StandInTransitionsMixin,
):
    """Provides pure state transition methods for GameSessionState."""

    @classmethod
    def initial(
        cls: type[GameSessionState],
        session_id: UUID,
        campaign_id: UUID,
        title: str,
        dm_id: str,
    ) -> GameSessionState:
        return cls(
            session_id=session_id,
            campaign_id=campaign_id,
            title=title,
            dm_id=dm_id,
            status="lobby",
            current_turn=1,
        )

    def with_status(self: GameSessionState, status: str) -> GameSessionState:
        return self.model_copy(update={"status": status})

    def with_started(
        self: GameSessionState, started_at_turn: int, active_character_id: UUID | None
    ) -> GameSessionState:
        return self.model_copy(
            update={
                "status": "active",
                "current_turn": started_at_turn,
                "active_character_id": active_character_id,
            }
        )

    def with_participant(
        self: GameSessionState,
        participant: ParticipantState,
        active_character_id: UUID | None,
    ) -> GameSessionState:
        participants = dict(self.participants)
        participants[participant.player_id] = participant
        return self.model_copy(
            update={
                "participants": participants,
                "active_character_id": active_character_id,
            }
        )

    def with_player_joined(self: GameSessionState, event: Any) -> GameSessionState:
        from game_session.models.session import ParticipantState

        participant = ParticipantState(
            player_id=event.player_id,
            character_id=event.character_id,
            character_name=event.character_name,
            character_class=event.character_class,
            is_present=True,
            is_stand_in_active=False,
        )
        active_id = self.active_character_id or event.character_id
        return self.with_participant(participant, active_id)

    def with_turn_advanced(
        self: GameSessionState, new_turn: int, active_character_id: UUID | None
    ) -> GameSessionState:
        return self.model_copy(
            update={"current_turn": new_turn, "active_character_id": active_character_id}
        )
