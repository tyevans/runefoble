"""Combat state transitions mixin for GameSessionState."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from game_session.models.session import GameSessionState


class CombatTransitionsMixin:
    """Transition methods for combat encounters and initiative progression."""

    def with_combat_started(
        self: GameSessionState, round_number: int, initiative_order: list[dict[str, Any]]
    ) -> GameSessionState:
        active_id = initiative_order[0]["combatant_id"] if initiative_order else None
        return self.model_copy(
            update={
                "in_combat": True,
                "combat_round": round_number,
                "initiative_order": initiative_order,
                "combat_active_id": active_id,
                "combat_turn_started": False,
            }
        )

    def with_initiative_rolled(
        self: GameSessionState, order: list[dict[str, Any]], active_id: str | None
    ) -> GameSessionState:
        return self.model_copy(update={"initiative_order": order, "combat_active_id": active_id})

    def with_initiative_turn_advanced(
        self: GameSessionState, round_number: int, active_combatant_id: str
    ) -> GameSessionState:
        return self.model_copy(
            update={
                "combat_round": round_number,
                "combat_active_id": active_combatant_id,
                "combat_turn_started": True,
            }
        )

    def with_combat_ended(self: GameSessionState) -> GameSessionState:
        return self.model_copy(
            update={"in_combat": False, "combat_active_id": None, "combat_turn_started": False}
        )
