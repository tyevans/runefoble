"""Root GameSessionAggregate combining session, combat, and reaction handler mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.aggregate.combat_handlers import CombatHandlersMixin
from game_session.aggregate.director_handlers import DirectorHandlersMixin
from game_session.aggregate.reaction_handlers import ReactionHandlersMixin
from game_session.aggregate.session_handlers import SessionHandlersMixin
from game_session.models import GameSessionState, ParticipantState
from game_session.rules import calculate_next_active_character
from runefoble_events.events import (
    DiceRolled,
    SessionEnded,
    StandInActionDecided,
    TurnAdvanced,
)

if TYPE_CHECKING:
    pass

__all__ = [
    "GameSessionAggregate",
    "GameSessionState",
    "ParticipantState",
]


class GameSessionAggregate(
    SessionHandlersMixin,
    CombatHandlersMixin,
    DirectorHandlersMixin,
    ReactionHandlersMixin,
    DeclarativeAggregate[GameSessionState],
):
    """Event-sourced aggregate managing tabletop game session lifecycle and turns."""

    aggregate_type = "GameSession"
    requires_creation_event = True

    def advance_turn(self, active_character_id: UUID | None = None) -> None:
        """Advance turn counter."""
        if self.state.status != "active":
            raise ValueError("Cannot advance turn in non-active session")
        prev = self.state.current_turn
        next_char_id = active_character_id
        if next_char_id is None:
            next_char_id = calculate_next_active_character(self.state.participants, prev)

        self.create_event(
            TurnAdvanced,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            previous_turn=prev,
            new_turn=prev + 1,
            active_character_id=next_char_id,
        )

    def record_dice_roll(
        self,
        roller_id: str,
        roller_name: str,
        formula: str,
        roll: dict[str, Any],
    ) -> None:
        """Record a dice roll evaluated by the caller. The session state does not change."""
        self.create_event(
            DiceRolled,
            campaign_id=self.state.campaign_id,
            session_id=str(self.aggregate_id),
            roller_id=roller_id,
            roller_name=roller_name,
            formula=formula,
            total=roll["total"],
            rolls=roll["rolls"],
            is_crit=roll.get("is_crit", False),
            is_fumble=roll.get("is_fumble", False),
        )

    def record_stand_in_action(
        self,
        character_name: str,
        action_type: str,
        dialogue: str,
        penalties_applied: list[str],
        flavor_text: str = "",
    ) -> None:
        """Record an autonomous stand-in action taken on behalf of an absent player."""
        self.create_event(
            StandInActionDecided,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            character_name=character_name,
            action_type=action_type,
            dialogue=dialogue,
            penalties_applied=penalties_applied,
            flavor_text=flavor_text,
        )

    def end(self, summary: str = "Session completed") -> None:
        """End the session. An ended session cannot end again."""
        if self.state.status == "ended":
            raise ValueError("Session already ended")
        self.create_event(
            SessionEnded,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            summary=summary,
        )

    @handles(DiceRolled)
    def _on_dice_rolled(self, event: DiceRolled) -> None:
        """Dice rolls do not change session state."""

    @handles(TurnAdvanced)
    def _on_turn_advanced(self, event: TurnAdvanced) -> None:
        self._state = self.state.with_turn_advanced(event.new_turn, event.active_character_id)

    @handles(StandInActionDecided)
    def _on_stand_in_action_decided(self, event: StandInActionDecided) -> None:
        self._state = self.state.with_stand_in_event(event)

    @handles(SessionEnded)
    def _on_ended(self, event: SessionEnded) -> None:
        self._state = self.state.with_status("ended")
