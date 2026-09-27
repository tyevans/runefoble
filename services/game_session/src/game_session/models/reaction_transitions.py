"""Reaction state transitions mixin for GameSessionState."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from game_session.models.session import GameSessionState


class ReactionTransitionsMixin:
    """Transition methods for spoken reaction interrupts and ready actions."""

    def with_turn_paused_for_reaction(
        self: GameSessionState, reaction_data: dict[str, Any]
    ) -> GameSessionState:
        return self.model_copy(
            update={"turn_paused_for_reaction": True, "active_reaction": reaction_data}
        )

    def with_reaction_resolved(
        self: GameSessionState, reaction_id: str, action_taken: str
    ) -> GameSessionState:
        return self.model_copy(update={"turn_paused_for_reaction": False, "active_reaction": None})

    def with_ready_action_registered(
        self: GameSessionState, ready_action_data: dict[str, Any]
    ) -> GameSessionState:
        target_id = ready_action_data.get("ready_action_id")
        actions = [a for a in self.ready_actions if a.get("ready_action_id") != target_id]
        actions.append(ready_action_data)
        return self.model_copy(update={"ready_actions": actions})

    def with_ready_action_triggered(
        self: GameSessionState, ready_action_id: str, triggering_data: dict[str, Any]
    ) -> GameSessionState:
        actions = [a for a in self.ready_actions if a.get("ready_action_id") != ready_action_id]
        return self.model_copy(update={"ready_actions": actions})
