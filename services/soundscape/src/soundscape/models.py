"""Pydantic models for soundscape REST requests, responses, and mixer state."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SoundscapeCueRequest(BaseModel):
    """Request model to trigger a tactical sound foley or acoustic cue."""

    session_id: str = Field(default="default", description="Associated game session ID")
    cue_name: str | None = Field(
        default=None, description="Preset sound cue identifier (e.g., fireball, sword_slash)"
    )
    sound_url: str | None = Field(
        default=None, description="Direct audio URL if not using a preset"
    )
    cue_type: str = Field(
        default="foley", description="Cue categorization: foley, sfx, stinger, spell, melee"
    )
    volume_gain: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Volume gain multiplier (1.0 = normal)"
    )
    duck_music: bool = Field(
        default=False, description="Whether to duck background music during this cue"
    )
    campaign_id: UUID | None = Field(
        default=None, description="Optional campaign ID for Zanzibar authorization"
    )


class SoundscapeCueResponse(BaseModel):
    """Response returned upon triggering a sound cue."""

    cue_id: str
    session_id: str
    status: str = "triggered"
    cue_name: str | None = None
    sound_url: str
    cue_type: str
    volume_gain: float
    duck_music: bool


class TensionCalculationRequest(BaseModel):
    """Request parameters for computing encounter tension."""

    session_id: str = Field(default="default", description="Game session ID")
    combat_active: bool = Field(
        default=False, description="Whether active initiative combat is underway"
    )
    combat_round: int = Field(default=1, ge=0, description="Current combat round")
    enemy_cr_balance: float = Field(
        default=1.0, ge=0.0, description="Total active enemy Challenge Rating ratio"
    )
    lowest_party_health_ratio: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Lowest current HP / Max HP among party members"
    )
    campaign_id: UUID | None = Field(
        default=None, description="Optional campaign ID for Zanzibar check"
    )


class MoodOverrideRequest(BaseModel):
    """DM request to manually force a specific soundscape mood or stem profile."""

    session_id: str = Field(default="default", description="Game session ID")
    mood: str = Field(..., description="Forced stem profile: exploration, tension, combat, boss")
    master_volume: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Optional master volume update (0.0 to 1.0)"
    )
    campaign_id: UUID | None = Field(
        default=None, description="Optional campaign ID for Zanzibar check"
    )


class DuckingRequest(BaseModel):
    """Request to toggle WebAudio ducking."""

    session_id: str = Field(default="default", description="Game session ID")
    is_ducked: bool = Field(
        ..., description="True to attenuate background music by -12dB; False to restore"
    )
    reason: str = Field(default="speech", description="Triggering source (speech, cue, vad)")


class StemVolumeUpdateRequest(BaseModel):
    """Request model to update multi-channel stem volumes."""

    session_id: str = Field(default="default", description="Associated game session ID")
    stem_volumes: dict[str, float] = Field(
        ...,
        description="Mapping of stem names (melody, percussion, drone, ambient) to volume (0.0 to 1.0)",
    )
    campaign_id: UUID | None = Field(
        default=None, description="Optional campaign ID for Zanzibar check"
    )


class TensionStatusResponse(BaseModel):
    """Current session tension status and audio stem weights."""

    session_id: str
    tension_score: int
    stem_profile: str
    active_stems: list[str]
    stem_volumes: dict[str, float]
    master_volume: float
    is_ducked: bool
    ducking_attenuation_db: float
    effective_gain: float
    manual_override: bool
    override_mood: str | None = None
    recent_cues: list[dict[str, Any]] = Field(default_factory=list)
