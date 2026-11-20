"""DM override and atmosphere state transitions for GameSessionState."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from game_session.models.session import GameSessionState

# The number of recorded board move ids that a session keeps for its redelivery guard.
CHRONICLED_MOVE_LIMIT = 1000


class DirectorTransitionsMixin:
    """Pure state transitions for DM overrides and the session atmosphere."""

    def with_dm_override(
        self: GameSessionState, action: str, reason: str | None, payload: dict[str, Any]
    ) -> GameSessionState:
        record = {"action": action, "reason": reason, "payload": payload}
        return self.model_copy(update={"dm_overrides": [*self.dm_overrides, record]})

    def with_atmosphere(self: GameSessionState, atmosphere: dict[str, Any]) -> GameSessionState:
        return self.model_copy(update={"atmosphere": atmosphere})

    def with_weather(
        self: GameSessionState, weather: str, source_proposal_id: str | None
    ) -> GameSessionState:
        return self.model_copy(
            update={"weather": weather, "weather_source_proposal_id": source_proposal_id}
        )

    def with_chronicled_move(self: GameSessionState, source_event_id: str) -> GameSessionState:
        ids = [*self.chronicled_move_ids, source_event_id][-CHRONICLED_MOVE_LIMIT:]
        return self.model_copy(update={"chronicled_move_ids": ids})
