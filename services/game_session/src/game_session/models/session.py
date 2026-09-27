"""Session configuration, participant status, and session metadata models."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from game_session.models.transitions import GameSessionTransitionsMixin
from pydantic import BaseModel, Field
from the_watcher.watcher_ai import StandInAction


class ParticipantState(BaseModel):
    player_id: str
    character_id: UUID
    character_name: str
    character_class: str
    is_present: bool = True
    is_stand_in_active: bool = False


class GameSessionState(BaseModel, GameSessionTransitionsMixin):
    session_id: UUID
    campaign_id: UUID
    title: str
    dm_id: str
    status: str = "lobby"
    current_turn: int = 1
    participants: dict[str, ParticipantState] = Field(default_factory=dict)
    active_character_id: UUID | None = None
    stand_in_actions: list[dict[str, Any]] = Field(default_factory=list)
    in_combat: bool = False
    combat_round: int = 1
    initiative_order: list[dict[str, Any]] = Field(default_factory=list)
    combat_active_id: str | None = None
    combat_turn_started: bool = False
    turn_paused_for_reaction: bool = False
    active_reaction: dict[str, Any] | None = None
    ready_actions: list[dict[str, Any]] = Field(default_factory=list)


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
