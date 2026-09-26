"""Domain models for The Watcher AI system."""

from typing import Any

from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    action_type: str  # "move", "attack", "cast_spell", "skill_check", "narrative", "roll_dice"
    confidence: float
    parameters: dict[str, Any] = Field(default_factory=dict)
    watcher_reply: str
    target: str | None = None
    details: str | None = None


class StandInAction(BaseModel):
    character_name: str
    action_type: str = "attack"
    action_description: str
    dialogue: str
    penalty_influence: str | None = None
    dice_roll_required: str | None = None
    penalties_applied: list[str] = Field(default_factory=list)
    flavor_text: str = ""


class StandInRecapResponse(BaseModel):
    character_name: str
    recap: str
    highlights: list[str] = Field(default_factory=list)
    penalties_active: list[str] = Field(default_factory=list)


class RecapRequest(BaseModel):
    session_id: str
    character_id: str
    character_name: str
    stand_in_persona: str = "valiant"
    penalties: list[str] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    hp_delta: int = 0
    items_acquired: list[str] = Field(default_factory=list)
    audio_url: str | None = None


class SceneGenerateRequest(BaseModel):
    session_id: str
    location_type: str = "dungeon"
    mood: str = "suspenseful"


class EncounterSpawnRequest(BaseModel):
    session_id: str
    scene_id: str = ""
    party_level: int = 3
    party_size: int = 4
    difficulty: str = "medium"


class NpcTurnRequest(BaseModel):
    session_id: str
    encounter_id: str
    actor_name: str
    targets: list[dict[str, Any]] = Field(default_factory=list)
    round_number: int = 1


