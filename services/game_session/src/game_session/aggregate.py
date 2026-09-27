"""Event-sourced GameSession aggregate using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.models import GameSessionState, ParticipantState
from game_session.rules import (
    advance_initiative_turn,
    calculate_next_active_character,
    resolve_initiative_rolled,
    sort_initiative_order,
)
from runefoble_events.events import (
    CharacterControlTransferred,
    CombatEncounterEnded,
    CombatEncounterStarted,
    CombatTurnPausedForReactionEvent,
    InitiativeRolled,
    InitiativeTurnAdvanced,
    PlayerJoinedSession,
    PlayerLeftSession,
    ReactionResolvedEvent,
    ReadyActionRegisteredEvent,
    ReadyActionTriggeredEvent,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    StandInActionDecided,
    TurnAdvanced,
)

__all__ = [
    "GameSessionAggregate",
    "GameSessionState",
    "ParticipantState",
]


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

    def hot_swap_character(self, player_id: str, character_id: UUID) -> None:
        """Transfer active token and turn control from AI stand-in back to player."""
        if self.state.status != "active":
            raise ValueError(f"Cannot hot-swap character in session status '{self.state.status}'")
        matching = None
        for pid, p in self.state.participants.items():
            if p.character_id == character_id or pid == player_id:
                matching = p
                break
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
        paused_combatant = self.state.combat_active_id or ""
        self.create_event(
            CombatTurnPausedForReactionEvent,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            reaction_id=reaction_id,
            reacting_combatant_id=reacting_combatant_id,
            reacting_combatant_name=reacting_combatant_name,
            trigger_phrase=trigger_phrase,
            reaction_type=reaction_type,
            paused_turn_combatant_id=paused_combatant,
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
        reacting_id = ""
        if (
            self.state.active_reaction
            and self.state.active_reaction.get("reaction_id") == reaction_id
        ):
            reacting_id = self.state.active_reaction.get("reacting_combatant_id", "")
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

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

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
            UUID(str(event.character_id))
            if not isinstance(event.character_id, UUID)
            else event.character_id
        )
        self._state = self.state.with_character_control_transferred(
            player_id=event.player_id,
            character_id=char_uuid,
        )

    @handles(TurnAdvanced)
    def _on_turn_advanced(self, event: TurnAdvanced) -> None:
        self._state = self.state.with_turn_advanced(event.new_turn, event.active_character_id)

    @handles(StandInActionDecided)
    def _on_stand_in_action_decided(self, event: StandInActionDecided) -> None:
        self._state = self.state.with_stand_in_event(event)

    @handles(SessionEnded)
    def _on_ended(self, event: SessionEnded) -> None:
        self._state = self.state.with_status("ended")

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

    @handles(CombatTurnPausedForReactionEvent)
    def _on_combat_turn_paused_for_reaction(self, event: CombatTurnPausedForReactionEvent) -> None:
        data = {
            "reaction_id": event.reaction_id,
            "reacting_combatant_id": event.reacting_combatant_id,
            "reacting_combatant_name": event.reacting_combatant_name,
            "trigger_phrase": event.trigger_phrase,
            "reaction_type": event.reaction_type,
            "paused_turn_combatant_id": event.paused_turn_combatant_id,
            "timeout_seconds": event.timeout_seconds,
            "details": event.details,
        }
        self._state = self.state.with_turn_paused_for_reaction(data)

    @handles(ReactionResolvedEvent)
    def _on_reaction_resolved(self, event: ReactionResolvedEvent) -> None:
        self._state = self.state.with_reaction_resolved(event.reaction_id, event.action_taken)

    @handles(ReadyActionRegisteredEvent)
    def _on_ready_action_registered(self, event: ReadyActionRegisteredEvent) -> None:
        data = {
            "ready_action_id": event.ready_action_id,
            "combatant_id": event.combatant_id,
            "combatant_name": event.combatant_name,
            "trigger_type": event.trigger_type,
            "trigger_condition": event.trigger_condition,
            "target_id": event.target_id,
            "range_cells": event.range_cells,
            "readied_action": event.readied_action,
            "details": event.details,
        }
        self._state = self.state.with_ready_action_registered(data)

    @handles(ReadyActionTriggeredEvent)
    def _on_ready_action_triggered(self, event: ReadyActionTriggeredEvent) -> None:
        data = {
            "ready_action_id": event.ready_action_id,
            "triggering_entity_id": event.triggering_entity_id,
            "trigger_type": event.trigger_type,
            "readied_action": event.readied_action,
            "details": event.details,
        }
        self._state = self.state.with_ready_action_triggered(event.ready_action_id, data)
