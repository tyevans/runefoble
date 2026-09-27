"""Reaction and ready-action domain handler mixin for GameSession aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.events import (
    CombatTurnPausedForReactionEvent,
    ReactionResolvedEvent,
    ReadyActionRegisteredEvent,
    ReadyActionTriggeredEvent,
)

if TYPE_CHECKING:
    from game_session.models import GameSessionState


def _extract(event: Any, fields: str) -> dict[str, Any]:
    return {f: getattr(event, f) for f in fields.split()}


class ReactionHandlersMixin:
    """Mixin providing reaction interruptions, pause/resume, and ready-action triggers."""

    _state: GameSessionState | None
    state: GameSessionState
    aggregate_id: Any
    create_event: Any

    def declare_reaction(
        self,
        reaction_id: str,
        reacting_combatant_id: str,
        reacting_combatant_name: str,
        trigger_phrase: str,
        reaction_type: str = "reaction",
        timeout_seconds: float = 15.0,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Halt active turn timer and initiate reaction window for spoken reaction."""
        self.create_event(
            CombatTurnPausedForReactionEvent,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            reaction_id=reaction_id,
            reacting_combatant_id=reacting_combatant_id,
            reacting_combatant_name=reacting_combatant_name,
            trigger_phrase=trigger_phrase,
            reaction_type=reaction_type,
            paused_turn_combatant_id=self.state.combat_active_id or "",
            timeout_seconds=timeout_seconds,
            details=details or {},
        )

    def resolve_reaction(
        self,
        reaction_id: str,
        action_taken: str = "executed",
        resumed: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Resolve or dismiss declared reaction interrupt, resuming active turn."""
        act = self.state.active_reaction
        reacting_id = (
            act.get("reacting_combatant_id", "")
            if act and act.get("reaction_id") == reaction_id
            else ""
        )
        self.create_event(
            ReactionResolvedEvent,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            reaction_id=reaction_id,
            reacting_combatant_id=reacting_id,
            action_taken=action_taken,
            resumed=resumed,
            details=details or {},
        )

    def register_ready_action(
        self,
        ready_action_id: str,
        combatant_id: str,
        combatant_name: str,
        trigger_type: str,
        trigger_condition: str,
        target_id: str | None = None,
        range_cells: int | None = None,
        readied_action: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Register conditional ready-action trigger for a combatant."""
        self.create_event(
            ReadyActionRegisteredEvent,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            ready_action_id=ready_action_id,
            combatant_id=combatant_id,
            combatant_name=combatant_name,
            trigger_type=trigger_type,
            trigger_condition=trigger_condition,
            target_id=target_id,
            range_cells=range_cells,
            readied_action=readied_action,
            details=details or {},
        )

    def trigger_ready_action(
        self,
        ready_action_id: str,
        combatant_id: str,
        combatant_name: str,
        triggering_entity_id: str,
        trigger_type: str,
        readied_action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Fire a triggered ready-action conditional trigger."""
        self.create_event(
            ReadyActionTriggeredEvent,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            ready_action_id=ready_action_id,
            combatant_id=combatant_id,
            combatant_name=combatant_name,
            triggering_entity_id=triggering_entity_id,
            trigger_type=trigger_type,
            readied_action=readied_action,
            details=details or {},
        )

    @handles(CombatTurnPausedForReactionEvent)
    def _on_combat_turn_paused_for_reaction(self, event: CombatTurnPausedForReactionEvent) -> None:
        fields = "reaction_id reacting_combatant_id reacting_combatant_name trigger_phrase reaction_type paused_turn_combatant_id timeout_seconds details"
        self._state = self.state.with_turn_paused_for_reaction(_extract(event, fields))

    @handles(ReactionResolvedEvent)
    def _on_reaction_resolved(self, event: ReactionResolvedEvent) -> None:
        self._state = self.state.with_reaction_resolved(event.reaction_id, event.action_taken)

    @handles(ReadyActionRegisteredEvent)
    def _on_ready_action_registered(self, event: ReadyActionRegisteredEvent) -> None:
        fields = "ready_action_id combatant_id combatant_name trigger_type trigger_condition target_id range_cells readied_action details"
        self._state = self.state.with_ready_action_registered(_extract(event, fields))

    @handles(ReadyActionTriggeredEvent)
    def _on_ready_action_triggered(self, event: ReadyActionTriggeredEvent) -> None:
        fields = "ready_action_id triggering_entity_id trigger_type readied_action details"
        self._state = self.state.with_ready_action_triggered(
            event.ready_action_id, _extract(event, fields)
        )
