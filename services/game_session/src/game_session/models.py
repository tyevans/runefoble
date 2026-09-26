"""Request, response, and domain state models for Game Session microservice."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from the_watcher.watcher_ai import StandInAction


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

    @classmethod
    def initial(
        cls, session_id: UUID, campaign_id: UUID, title: str, dm_id: str
    ) -> "GameSessionState":
        return cls(
            session_id=session_id,
            campaign_id=campaign_id,
            title=title,
            dm_id=dm_id,
            status="lobby",
            current_turn=1,
        )

    def with_status(self, status: str) -> "GameSessionState":
        return self.model_copy(update={"status": status})

    def with_started(
        self, started_at_turn: int, active_character_id: UUID | None
    ) -> "GameSessionState":
        return self.model_copy(
            update={
                "status": "active",
                "current_turn": started_at_turn,
                "active_character_id": active_character_id,
            }
        )

    def with_participant(
        self, participant: ParticipantState, active_character_id: UUID | None
    ) -> "GameSessionState":
        participants = dict(self.participants)
        participants[participant.player_id] = participant
        return self.model_copy(
            update={"participants": participants, "active_character_id": active_character_id}
        )

    def with_player_joined(self, event: Any) -> "GameSessionState":
        participant = ParticipantState(
            player_id=event.player_id,
            character_id=event.character_id,
            character_name=event.character_name,
            character_class=event.character_class,
            is_present=True,
            is_stand_in_active=False,
        )
        active_id = self.active_character_id or event.character_id
        return self.with_participant(participant, active_id)

    def without_player_presence(self, player_id: str) -> "GameSessionState":
        participants = dict(self.participants)
        if player_id in participants:
            p = participants[player_id]
            participants[player_id] = p.model_copy(
                update={"is_present": False, "is_stand_in_active": True}
            )
        return self.model_copy(update={"participants": participants})

    def with_character_control_transferred(
        self, player_id: str, character_id: UUID
    ) -> "GameSessionState":
        participants = dict(self.participants)
        if player_id in participants:
            p = participants[player_id]
            participants[player_id] = p.model_copy(
                update={"is_present": True, "is_stand_in_active": False}
            )
        else:
            for pid, p in list(participants.items()):
                if p.character_id == character_id:
                    participants[pid] = p.model_copy(
                        update={
                            "is_present": True,
                            "is_stand_in_active": False,
                            "player_id": player_id,
                        }
                    )
                    break
        return self.model_copy(update={"participants": participants})

    def with_turn_advanced(
        self, new_turn: int, active_character_id: UUID | None
    ) -> "GameSessionState":
        return self.model_copy(
            update={
                "current_turn": new_turn,
                "active_character_id": active_character_id,
            }
        )

    def with_stand_in_event(self, event: Any) -> "GameSessionState":
        return self.with_stand_in_action(
            {
                "character_name": event.character_name,
                "action_type": event.action_type,
                "dialogue": event.dialogue,
                "penalties_applied": event.penalties_applied,
                "flavor_text": event.flavor_text,
            }
        )

    def with_stand_in_action(self, action: dict[str, Any]) -> "GameSessionState":
        actions = list(self.stand_in_actions)
        actions.append(action)
        return self.model_copy(update={"stand_in_actions": actions})

    def with_combat_started(
        self, round_number: int, initiative_order: list[dict[str, Any]]
    ) -> "GameSessionState":
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
        self, order: list[dict[str, Any]], active_id: str | None
    ) -> "GameSessionState":
        return self.model_copy(
            update={
                "initiative_order": order,
                "combat_active_id": active_id,
            }
        )

    def with_initiative_turn_advanced(
        self, round_number: int, active_combatant_id: str
    ) -> "GameSessionState":
        return self.model_copy(
            update={
                "combat_round": round_number,
                "combat_active_id": active_combatant_id,
                "combat_turn_started": True,
            }
        )

    def with_combat_ended(self) -> "GameSessionState":
        return self.model_copy(
            update={
                "in_combat": False,
                "combat_active_id": None,
                "combat_turn_started": False,
            }
        )


class CreateSessionRequest(BaseModel):
    campaign_id: UUID
    title: str = "Tomb of the Star-Eater - Session 1"
    dm_id: str = "the_watcher"


class JoinSessionRequest(BaseModel):
    player_id: str
    character_id: UUID
    character_name: str
    character_class: str


class LeaveSessionRequest(BaseModel):
    player_id: str
    reason: str = "disconnected"


class AutoPilotRequest(BaseModel):
    active_character_id: UUID | None = None
    penalties: list[str] = Field(default_factory=list)
    scene_context: str = "In active encounter"
    personality_traits: list[str] = Field(default_factory=list)
    guardrails: dict[str, Any] | None = None


class AutoPilotResponse(BaseModel):
    session_id: UUID
    current_turn: int
    action: StandInAction
    stand_in_action: StandInAction
    session_state: GameSessionState


class StartCombatRequest(BaseModel):
    combatants: list[dict[str, Any]] = Field(default_factory=list)


class InitiativeRollRequest(BaseModel):
    combatant_id: str
    combatant_name: str
    initiative_score: float | int
    is_npc: bool = False


class NextTurnRequest(BaseModel):
    turn_seconds: int = 60


class CombatStateResponse(BaseModel):
    session_id: UUID
    in_combat: bool
    combat_round: int
    combat_active_id: str | None
    initiative_order: list[dict[str, Any]]
    turn_seconds_remaining: int = 60


class RollDiceRequest(BaseModel):
    formula: str = "1d20"
    roller_id: str = "player"
    roller_name: str = "Player"
    roll_type: str = "general"


class RollDiceResponse(BaseModel):
    session_id: UUID
    roller_id: str
    roller_name: str
    formula: str
    total: int
    rolls: list[int] = Field(default_factory=list)
    is_crit: bool = False
    is_fumble: bool = False
    roll_type: str = "general"


class HotSwapRequest(BaseModel):
    player_id: str
    character_id: UUID


class HotSwapResponse(BaseModel):
    session_id: UUID
    character_id: UUID
    player_id: str
    previous_controller: str = "ai_stand_in"
    new_controller: str = "player"
    current_turn: int
    in_combat: bool
    combat_round: int
    combat_active_id: str | None
    session_state: GameSessionState
