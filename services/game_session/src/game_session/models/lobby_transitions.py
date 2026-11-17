"""Lobby readiness and lobby character state transitions for GameSessionState."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from game_session.models.session import GameSessionState


class LobbyTransitionsMixin:
    """Provides pure state transitions for lobby readiness and lobby character selection."""

    def with_readiness(self: GameSessionState, player_id: str, is_ready: bool) -> GameSessionState:
        readiness = dict(self.lobby_readiness)
        readiness[player_id] = is_ready
        return self.model_copy(update={"lobby_readiness": readiness})

    def with_lobby_character(
        self: GameSessionState, player_id: str, character_id: UUID
    ) -> GameSessionState:
        characters = dict(self.lobby_characters)
        characters[player_id] = character_id
        return self.model_copy(update={"lobby_characters": characters})
