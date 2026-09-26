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
    guardrails_applied: list[str] = Field(default_factory=list)
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


class SpeechInputRequest(BaseModel):
    speaker_id: str
    speaker_name: str
    transcript: str
    session_id: str
    campaign_id: str
    token_id: str | None = None
    from_x: int | None = None
    from_y: int | None = None
    grid_cols: int = 12
    grid_rows: int = 12


class StandInRequest(BaseModel):
    character_name: str
    character_class: str
    penalties: list[str] = Field(default_factory=list)
    scene_context: str = "In combat with subterranean creatures"
    personality_traits: list[str] = Field(default_factory=list)
    guardrails: dict[str, Any] | None = None
    session_id: str | None = None
    campaign_id: str | None = None


class StandInRecapRequest(BaseModel):
    character_name: str
    actions: list[Any] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)


class DMGuidanceRequest(BaseModel):
    session_id: str
    prompt: str


class EntityTarget(BaseModel):
    id: str
    name: str
    tag: str | None = None
    descriptor: str | None = None
    x: int = 0
    y: int = 0
    hp: int | None = None
    is_friendly: bool = False


class CandidateTarget(BaseModel):
    id: str
    name: str
    tag: str | None = None
    descriptor: str
    x: int = 0
    y: int = 0
    distance_ft: int | None = None
    preview_coordinates: tuple[int, int] | None = None


class CompoundActionNode(BaseModel):
    node_id: str
    order: int
    action_type: str  # "move", "skill_check", "attack", "cast_spell", "roll_dice", "narrative"
    parameters: dict[str, Any] = Field(default_factory=dict)
    target: str | None = None
    description: str = ""
    status: str = "pending"  # "pending", "completed", "failed", "aborted", "rolled_back"
    requires_disambiguation: bool = False
    candidates: list[CandidateTarget] = Field(default_factory=list)


class IntentParseRequest(BaseModel):
    speaker_id: str
    speaker_name: str
    transcript: str
    session_id: str
    campaign_id: str | None = None
    token_id: str | None = None
    from_x: int | None = None
    from_y: int | None = None
    grid_cols: int = 12
    grid_rows: int = 12
    entities: list[EntityTarget] = Field(default_factory=list)
    tokens: list[EntityTarget] = Field(default_factory=list)


class IntentParseResponse(BaseModel):
    session_id: str
    speaker_name: str
    transcript: str
    requires_disambiguation: bool = False
    disambiguation_id: str | None = None
    clarification_prompt: str | None = None
    candidates: list[CandidateTarget] = Field(default_factory=list)
    is_compound: bool = False
    actions: list[CompoundActionNode] = Field(default_factory=list)
    single_intent: IntentResult | None = None
    execution_latency_ms: float = 0.0


class IntentResolveRequest(BaseModel):
    session_id: str
    campaign_id: str | None = None
    disambiguation_id: str
    speaker_id: str | None = None
    speaker_name: str | None = None
    selected_candidate_id: str | None = None
    selected_target: str | None = None
    execute_immediately: bool = False
    step_results: dict[str, bool] = Field(default_factory=dict)


class IntentResolveResponse(BaseModel):
    session_id: str
    disambiguation_id: str
    resolved_target: str
    status: str = "ready"  # "ready", "executing", "completed", "partial_failure"
    actions: list[CompoundActionNode] = Field(default_factory=list)
    narrative_summary: str = ""
    execution_latency_ms: float = 0.0


class IntentExecuteRequest(BaseModel):
    session_id: str
    campaign_id: str | None = None
    speaker_name: str = "Player"
    actions: list[CompoundActionNode] = Field(default_factory=list)
    step_results: dict[str, bool] = Field(default_factory=dict)
    rollback_on_failure: bool = True


class IntentExecuteResponse(BaseModel):
    session_id: str
    status: str = "completed"  # "completed", "partial_failure", "rolled_back"
    actions: list[CompoundActionNode] = Field(default_factory=list)
    narrative_summary: str = ""
    failed_node_id: str | None = None
