"""Event-sourced GameSession aggregate using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    PlayerJoinedSession,
    PlayerLeftSession,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    StandInActionDecided,
    TurnAdvanced,
)


class ParticipantState(BaseModel):
    player_id: str
    character_id: UUID
    character_name: str
    character_class: str
    is_present: bool = True
    is_stand_in_active: bool = False


class GameSessionState(BaseModel):
    session_id: UUID
    campaign_id: UUID
    title: str
    dm_id: str
    status: str = "lobby"  # lobby, active, ended
    current_turn: int = 1
    participants: dict[str, ParticipantState] = Field(default_factory=dict)
    active_character_id: UUID | None = None
    stand_in_actions: list[dict[str, Any]] = Field(default_factory=list)


class GameSessionAggregate(DeclarativeAggregate[GameSessionState]):
    """Event-sourced aggregate managing tabletop game session lifecycle and turns."""

    aggregate_type = "GameSession"
    requires_creation_event = True

    def create(self, campaign_id: UUID, title: str, dm_id: str = "the_watcher") -> None:
        """Create new game session."""
        self.create_event(
            SessionCreated,
            campaign_id=campaign_id,
            session_id=self.aggregate_id,
            title=title,
            dm_id=dm_id,
        )

    def start(self) -> None:
        """Start session."""
        if self.state.status != "lobby":
            raise ValueError(f"Cannot start session in status '{self.state.status}'")
        self.create_event(
            SessionStarted,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            started_at_turn=1,
        )

    def join_player(
        self,
        player_id: str,
        character_id: UUID,
        character_name: str,
        character_class: str,
    ) -> None:
        """Record player joining the session."""
        self.create_event(
            PlayerJoinedSession,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            player_id=player_id,
            character_id=character_id,
            character_name=character_name,
            character_class=character_class,
        )

    def leave_player(self, player_id: str, reason: str = "disconnected") -> None:
        """Record player leaving or absent, enabling AI stand-in."""
        if player_id not in self.state.participants:
            raise ValueError(f"Player {player_id} is not in session")
        self.create_event(
            PlayerLeftSession,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            player_id=player_id,
            reason=reason,
        )

    def advance_turn(self, active_character_id: UUID | None = None) -> None:
        """Advance turn counter."""
        if self.state.status != "active":
            raise ValueError("Cannot advance turn in non-active session")
        prev = self.state.current_turn
        next_char_id = active_character_id
        if next_char_id is None and self.state.participants:
            part_list = list(self.state.participants.values())
            next_idx = prev % len(part_list)
            next_char_id = part_list[next_idx].character_id

        self.create_event(
            TurnAdvanced,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            previous_turn=prev,
            new_turn=prev + 1,
            active_character_id=next_char_id,
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
        """End the session."""
        self.create_event(
            SessionEnded,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            summary=summary,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(SessionCreated)
    def _on_created(self, event: SessionCreated) -> None:
        self._state = GameSessionState(
            session_id=event.aggregate_id,
            campaign_id=event.campaign_id or event.aggregate_id,
            title=event.title,
            dm_id=event.dm_id,
            status="lobby",
            current_turn=1,
        )

    @handles(SessionStarted)
    def _on_started(self, event: SessionStarted) -> None:
        active_id = self.state.active_character_id
        if active_id is None and self.state.participants:
            active_id = next(iter(self.state.participants.values())).character_id
        self._state = self.state.model_copy(
            update={
                "status": "active",
                "current_turn": event.started_at_turn,
                "active_character_id": active_id,
            }
        )

    @handles(PlayerJoinedSession)
    def _on_player_joined(self, event: PlayerJoinedSession) -> None:
        participants = dict(self.state.participants)
        participants[event.player_id] = ParticipantState(
            player_id=event.player_id,
            character_id=event.character_id,
            character_name=event.character_name,
            character_class=event.character_class,
            is_present=True,
            is_stand_in_active=False,
        )
        active_id = self.state.active_character_id or event.character_id
        self._state = self.state.model_copy(
            update={"participants": participants, "active_character_id": active_id}
        )

    @handles(PlayerLeftSession)
    def _on_player_left(self, event: PlayerLeftSession) -> None:
        participants = dict(self.state.participants)
        if event.player_id in participants:
            p = participants[event.player_id]
            participants[event.player_id] = p.model_copy(
                update={"is_present": False, "is_stand_in_active": True}
            )
        self._state = self.state.model_copy(update={"participants": participants})

    @handles(TurnAdvanced)
    def _on_turn_advanced(self, event: TurnAdvanced) -> None:
        self._state = self.state.model_copy(
            update={
                "current_turn": event.new_turn,
                "active_character_id": event.active_character_id,
            }
        )

    @handles(StandInActionDecided)
    def _on_stand_in_action_decided(self, event: StandInActionDecided) -> None:
        actions = list(self.state.stand_in_actions)
        actions.append(
            {
                "character_name": event.character_name,
                "action_type": event.action_type,
                "dialogue": event.dialogue,
                "penalties_applied": event.penalties_applied,
                "flavor_text": event.flavor_text,
            }
        )
        self._state = self.state.model_copy(update={"stand_in_actions": actions})

    @handles(SessionEnded)
    def _on_ended(self, event: SessionEnded) -> None:
        self._state = self.state.model_copy(update={"status": "ended"})
