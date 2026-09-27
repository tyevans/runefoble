"""Initiative roll and dice models for Game Session microservice."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class InitiativeRollRequest(BaseModel):
    combatant_id: str
    combatant_name: str
    initiative_score: float | int
    is_npc: bool = False


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
