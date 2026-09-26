"""Request and response models for Game Session microservice."""

from typing import Any
from uuid import UUID

from game_session.aggregate import GameSessionState
from pydantic import BaseModel, Field
from the_watcher.watcher_ai import StandInAction


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
