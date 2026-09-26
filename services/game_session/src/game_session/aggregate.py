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
    InitiativeRolled,
    InitiativeTurnAdvanced,
    PlayerJoinedSession,
    PlayerLeftSession,
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
