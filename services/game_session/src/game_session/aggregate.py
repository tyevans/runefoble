"""Event-sourced GameSession aggregate using eventsource-py."""

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
        self.create_event(
            TurnAdvanced,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            previous_turn=prev,
            new_turn=prev + 1,
            active_character_id=active_character_id,
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
        self._state = self.state.model_copy(
            update={"status": "active", "current_turn": event.started_at_turn}
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
        self._state = self.state.model_copy(update={"participants": participants})

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

    @handles(SessionEnded)
    def _on_ended(self, event: SessionEnded) -> None:
        self._state = self.state.model_copy(update={"status": "ended"})
