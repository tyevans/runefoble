"""Data models and schemas for Runefoble AI Inference Worker."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenContext(BaseModel):
    token_id: str
    name: str
    token_type: Literal["pc", "monster", "npc", "obstacle"]
    x: int
    y: int
    hp: int | None = None
    is_friendly: bool = False


class IntentParseRequest(BaseModel):
    """Request payload to parse natural player speech or text into structured action."""

    campaign_id: str = Field(..., description="Active campaign UUID")
    session_id: str = Field(..., description="Active session UUID")
    speaker_id: str = Field(..., description="User or character ID speaking")
    speaker_name: str = Field(..., description="Name of the player character")
    transcript: str = Field(..., description="Raw text or STT transcript")
    visible_tokens: list[TokenContext] = Field(
        default_factory=list,
        description="Visible tokens currently on tactical grid",
    )
    character_class: str | None = Field(default=None, description="Class of character")


class ParsedAction(BaseModel):
    action_type: Literal[
        "attack",
        "cast_spell",
        "move",
        "dash",
        "dodge",
        "help",
        "skill_check",
        "dialogue",
        "unknown",
    ]
    target_token_id: str | None = None
    target_token_name: str | None = None
    target_x: int | None = None
    target_y: int | None = None
    spell_or_ability: str | None = None
    dice_check_required: str | None = Field(
        default=None,
        description="e.g. '1d20+5' or 'DC 14 Dexterity save'",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    narrative_flavor: str = Field(default="", description="Atmospheric flavor description")
    raw_transcript: str = ""


class IntentParseResponse(BaseModel):
    session_id: str
    speaker_name: str
    action: ParsedAction
    execution_time_ms: float = 0.0


class DMNarrationRequest(BaseModel):
    """Request payload for autonomous DM scene narration and event resolution."""

    campaign_id: str
    session_id: str
    recent_events: list[str] = Field(
        default_factory=list,
        description="Chronological log of recent tactical or dialogue events",
    )
    scene_environment: str = Field(
        default="Dungeon chamber",
        description="Physical setting description",
    )
    tone: Literal["dark_fantasy", "epic_heroic", "tense_mystery", "whimsical", "gritty"] = (
        "dark_fantasy"
    )
    guidance_prompt: str | None = Field(
        default=None,
        description="Specific DM trigger or player query",
    )


class DMNarrationResponse(BaseModel):
    session_id: str
    narration: str
    sensory_details: list[str] = Field(default_factory=list)
    suggested_dm_prompts: list[str] = Field(default_factory=list)
    tension_level: Literal["calm", "rising", "climax", "aftermath"] = "rising"


class StandInActionRequest(BaseModel):
    """Request to generate an action for an absent player's character."""

    campaign_id: str
    session_id: str
    character_name: str
    character_class: str
    personality_traits: list[str] = Field(
        default_factory=lambda: ["valiant", "impulsive"],
        description="Core personality traits to mimic",
    )
    penalties: list[str] = Field(
        default_factory=list,
        description="Session-miss penalties imposed by DM (e.g. 'drunk', 'foolishness')",
    )
    scene_context: str = "Surrounded by hostile creatures"
    visible_enemies: list[str] = Field(default_factory=list)
    visible_allies: list[str] = Field(default_factory=list)


class StandInActionResponse(BaseModel):
    session_id: str
    character_name: str
    action_type: Literal["attack", "cast_spell", "move", "flee", "foolish_act", "blunder"]
    target: str | None = None
    dialogue: str
    narrative_flavor: str
    penalties_applied: list[str]
    mechanics: dict[str, Any] = Field(default_factory=dict)
