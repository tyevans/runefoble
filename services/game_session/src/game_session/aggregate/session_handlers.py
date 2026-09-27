"""Session lifecycle domain handler mixin for GameSession aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from eventsource.domain.decorators import handles
from game_session.models import GameSessionState
from runefoble_events.events import (
    CharacterControlTransferred,
    PlayerJoinedSession,
    PlayerLeftSession,
    SessionCreated,
    SessionStarted,
)

if TYPE_CHECKING:
    pass


class SessionHandlersMixin:
    """Mixin providing session creation, starting, player joining, and hot-swapping."""

    _state: GameSessionState | None
    state: GameSessionState
    aggregate_id: Any
    create_event: Any

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

    def hot_swap_character(self, player_id: str, character_id: UUID) -> None:
        """Transfer active token and turn control from AI stand-in back to player."""
        if self.state.status != "active":
            raise ValueError(f"Cannot hot-swap character in session status '{self.state.status}'")
        matching = next(
            (
                p
                for pid, p in self.state.participants.items()
                if p.character_id == character_id or pid == player_id
            ),
            None,
        )
        if matching is None:
            raise ValueError(f"Character '{character_id}' is not in session")

        self.create_event(
            CharacterControlTransferred,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            character_id=character_id,
            player_id=player_id,
            previous_controller="ai_stand_in",
            new_controller="player",
        )

    @handles(SessionCreated)
    def _on_created(self, event: SessionCreated) -> None:
        self._state = GameSessionState.initial(
            session_id=event.aggregate_id,
            campaign_id=event.campaign_id or event.aggregate_id,
            title=event.title,
            dm_id=event.dm_id,
        )

    @handles(SessionStarted)
    def _on_started(self, event: SessionStarted) -> None:
        active_id = self.state.active_character_id
        if active_id is None and self.state.participants:
            active_id = next(iter(self.state.participants.values())).character_id
        self._state = self.state.with_started(event.started_at_turn, active_id)

    @handles(PlayerJoinedSession)
    def _on_player_joined(self, event: PlayerJoinedSession) -> None:
        self._state = self.state.with_player_joined(event)

    @handles(PlayerLeftSession)
    def _on_player_left(self, event: PlayerLeftSession) -> None:
        self._state = self.state.without_player_presence(event.player_id)

    @handles(CharacterControlTransferred)
    def _on_control_transferred(self, event: CharacterControlTransferred) -> None:
        char_uuid = (
            event.character_id
            if isinstance(event.character_id, UUID)
            else UUID(str(event.character_id))
        )
        self._state = self.state.with_character_control_transferred(
            player_id=event.player_id,
            character_id=char_uuid,
        )
