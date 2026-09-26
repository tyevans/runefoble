"""Event-sourced GameSession aggregate using eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
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
    stand_in_actions: list[dict[str, Any]] = Field(default_factory=list)
    in_combat: bool = False
    combat_round: int = 1
    initiative_order: list[dict[str, Any]] = Field(default_factory=list)
    combat_active_id: str | None = None
    combat_turn_started: bool = False


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
        next_char_id = active_character_id
        if next_char_id is None and self.state.participants:
            part_list = list(self.state.participants.values())
            next_idx = prev % len(part_list)
            next_char_id = part_list[next_idx].character_id

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
        if not self.state.initiative_order:
            raise ValueError("Cannot advance initiative: initiative order is empty")

        sorted_order = sorted(
            self.state.initiative_order,
            key=lambda c: (
                c.get("initiative_score", 0),
                1 if not c.get("is_npc", False) else 0,
                c.get("combatant_name", ""),
            ),
            reverse=True,
        )

        curr_id = self.state.combat_active_id
        ids = [c["combatant_id"] for c in sorted_order]

        if curr_id in ids:
            curr_idx = ids.index(curr_id)
            next_idx = (curr_idx + 1) % len(ids)
            next_round = self.state.combat_round + 1 if next_idx == 0 else self.state.combat_round
        else:
            next_idx = 0
            next_round = self.state.combat_round

        next_active_id = ids[next_idx]

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
        active_id = self.state.active_character_id
        if active_id is None and self.state.participants:
            active_id = next(iter(self.state.participants.values())).character_id
        self._state = self.state.model_copy(
            update={
                "status": "active",
                "current_turn": event.started_at_turn,
                "active_character_id": active_id,
            }
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
        active_id = self.state.active_character_id or event.character_id
        self._state = self.state.model_copy(
            update={"participants": participants, "active_character_id": active_id}
        )

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

    @handles(StandInActionDecided)
    def _on_stand_in_action_decided(self, event: StandInActionDecided) -> None:
        actions = list(self.state.stand_in_actions)
        actions.append(
            {
                "character_name": event.character_name,
                "action_type": event.action_type,
                "dialogue": event.dialogue,
                "penalties_applied": event.penalties_applied,
                "flavor_text": event.flavor_text,
            }
        )
        self._state = self.state.model_copy(update={"stand_in_actions": actions})

    @handles(SessionEnded)
    def _on_ended(self, event: SessionEnded) -> None:
        self._state = self.state.model_copy(update={"status": "ended"})

    @handles(CombatEncounterStarted)
    def _on_combat_started(self, event: CombatEncounterStarted) -> None:
        initial_order: list[dict[str, Any]] = []
        if event.combatants:
            initial_order = list(event.combatants)
            initial_order.sort(
                key=lambda c: (
                    c.get("initiative_score", 0),
                    1 if not c.get("is_npc", False) else 0,
                    c.get("combatant_name", ""),
                ),
                reverse=True,
            )
        active_id = initial_order[0]["combatant_id"] if initial_order else None
        self._state = self.state.model_copy(
            update={
                "in_combat": True,
                "combat_round": event.round_number,
                "initiative_order": initial_order,
                "combat_active_id": active_id,
                "combat_turn_started": False,
            }
        )

    @handles(InitiativeRolled)
    def _on_initiative_rolled(self, event: InitiativeRolled) -> None:
        existing_combatants = [
            c for c in self.state.initiative_order if c["combatant_id"] != event.combatant_id
        ]
        new_entry = {
            "combatant_id": event.combatant_id,
            "combatant_name": event.combatant_name,
            "initiative_score": event.initiative_score,
            "is_npc": event.is_npc,
        }
        order = existing_combatants + [new_entry]
        order.sort(
            key=lambda c: (
                c.get("initiative_score", 0),
                1 if not c.get("is_npc", False) else 0,
                c.get("combatant_name", ""),
            ),
            reverse=True,
        )
        active_id = (
            self.state.combat_active_id
            if self.state.combat_turn_started
            else (order[0]["combatant_id"] if order else None)
        )
        self._state = self.state.model_copy(
            update={
                "initiative_order": order,
                "combat_active_id": active_id,
            }
        )

    @handles(InitiativeTurnAdvanced)
    def _on_initiative_turn_advanced(self, event: InitiativeTurnAdvanced) -> None:
        self._state = self.state.model_copy(
            update={
                "combat_round": event.round_number,
                "combat_active_id": event.active_combatant_id,
                "combat_turn_started": True,
            }
        )

    @handles(CombatEncounterEnded)
    def _on_combat_ended(self, event: CombatEncounterEnded) -> None:
        self._state = self.state.model_copy(
            update={
                "in_combat": False,
                "combat_active_id": None,
                "combat_turn_started": False,
            }
        )


