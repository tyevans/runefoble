"""Reaction declarations, ready action triggers, and interrupt state models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from game_session.models.session import GameSessionState


class DeclareReactionRequest(BaseModel):
    reacting_combatant_id: str
    reacting_combatant_name: str = ""
    trigger_phrase: str
    reaction_type: str = "reaction"
    timeout_seconds: float = 15.0
    target_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DeclareReactionResponse(BaseModel):
    session_id: UUID
    reaction_id: str
    status: str = "paused"
    reacting_combatant_id: str
    reacting_combatant_name: str = ""
    paused_turn_combatant_id: str | None = None
    reaction_type: str = "reaction"
    timeout_seconds: float = 15.0
    message: str = "Turn paused for reaction"


class ReadyActionRequest(BaseModel):
    combatant_id: str
    combatant_name: str = ""
    trigger_type: str = "spatial"
    trigger_condition: str
    readied_action: str
    target_id: str | None = None
    range_cells: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ReadyActionResponse(BaseModel):
    session_id: UUID
    ready_action_id: str
    combatant_id: str
    combatant_name: str
    trigger_type: str
    trigger_condition: str
    readied_action: str
    status: str = "registered"
    message: str = "Ready-action trigger registered"


class ResolveReactionRequest(BaseModel):
    action_taken: str = "executed"
    details: dict[str, Any] = Field(default_factory=dict)


class ResolveReactionResponse(BaseModel):
    session_id: UUID
    reaction_id: str
    status: str = "resolved"
    resumed: bool = True
    action_taken: str = "executed"
    message: str = "Reaction resolved and turn resumed"
    session_state: GameSessionState | None = None


class EvaluateTriggersRequest(BaseModel):
    event_type: str
    event_data: dict[str, Any] = Field(default_factory=dict)


class EvaluateTriggersResponse(BaseModel):
    session_id: UUID
    triggered_count: int
    triggered_actions: list[dict[str, Any]] = Field(default_factory=list)
