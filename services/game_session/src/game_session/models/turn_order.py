"""Turn order progression and combat encounter state schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class StartCombatRequest(BaseModel):
    combatants: list[dict[str, Any]] = Field(default_factory=list)


class NextTurnRequest(BaseModel):
    turn_seconds: int = 60


class CombatStateResponse(BaseModel):
    session_id: UUID
    in_combat: bool
    combat_round: int
    combat_active_id: str | None
    initiative_order: list[dict[str, Any]]
    turn_seconds_remaining: int = 60
