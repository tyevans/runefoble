"""Combat and initiative domain handler mixin for GameSession aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from game_session.rules import (
    advance_initiative_turn,
    resolve_initiative_rolled,
    sort_initiative_order,
)
from runefoble_events.events import (
    CombatEncounterEnded,
    CombatEncounterStarted,
    InitiativeRolled,
    InitiativeTurnAdvanced,
)

if TYPE_CHECKING:
    from game_session.models import GameSessionState


class CombatHandlersMixin:
    """Mixin providing combat encounter initiation, initiative ordering, and turn cycles."""

    _state: GameSessionState | None
    state: GameSessionState
    aggregate_id: Any
    create_event: Any

    def start_combat(self, combatants: list[dict[str, Any]] | None = None) -> None:
        """Start a combat encounter with turn order and initiative tracking."""
        if self.state.status == "ended":
            raise ValueError("Cannot start combat in an ended session")
        self.create_event(
            CombatEncounterStarted,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            round_number=1,
            combatants=combatants or [],
        )

    def roll_initiative(
        self,
        combatant_id: str,
        combatant_name: str,
        initiative_score: float | int,
        is_npc: bool = False,
    ) -> None:
        """Record or update combatant initiative score."""
        if not self.state.in_combat:
            raise ValueError("Cannot roll initiative: encounter not in combat")
        self.create_event(
            InitiativeRolled,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            combatant_id=str(combatant_id),
            combatant_name=combatant_name,
            initiative_score=initiative_score,
            is_npc=is_npc,
        )

    def advance_initiative(self, turn_seconds_remaining: int = 60) -> None:
        """Advance combat turn to next combatant in initiative order, incrementing round on loop."""
        if not self.state.in_combat:
            raise ValueError("Cannot advance initiative: encounter not in combat")

        next_active_id, next_round = advance_initiative_turn(
            self.state.initiative_order, self.state.combat_active_id, self.state.combat_round
        )

        self.create_event(
            InitiativeTurnAdvanced,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            round_number=next_round,
            active_combatant_id=next_active_id,
            turn_seconds_remaining=turn_seconds_remaining,
        )

    def end_combat(self) -> None:
        """End the active combat encounter."""
        if not self.state.in_combat:
            raise ValueError("Cannot end combat: not in combat")
        self.create_event(
            CombatEncounterEnded,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            total_rounds=self.state.combat_round,
        )

    @handles(CombatEncounterStarted)
    def _on_combat_started(self, event: CombatEncounterStarted) -> None:
        order = sort_initiative_order(list(event.combatants)) if event.combatants else []
        self._state = self.state.with_combat_started(event.round_number, order)

    @handles(InitiativeRolled)
    def _on_initiative_rolled(self, event: InitiativeRolled) -> None:
        order, active_id = resolve_initiative_rolled(
            self.state.initiative_order,
            self.state.combat_active_id,
            self.state.combat_turn_started,
            event.combatant_id,
            event.combatant_name,
            event.initiative_score,
            event.is_npc,
        )
        self._state = self.state.with_initiative_rolled(order, active_id)

    @handles(InitiativeTurnAdvanced)
    def _on_initiative_turn_advanced(self, event: InitiativeTurnAdvanced) -> None:
        self._state = self.state.with_initiative_turn_advanced(
            round_number=event.round_number, active_combatant_id=event.active_combatant_id
        )

    @handles(CombatEncounterEnded)
    def _on_combat_ended(self, event: CombatEncounterEnded) -> None:
        self._state = self.state.with_combat_ended()
