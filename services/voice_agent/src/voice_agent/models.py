"""Pydantic schemas and domain models for Voice Agent service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VoicePersona(BaseModel):
    id: str
    name: str
    description: str
    pitch_modifier: float = 1.0
    speed_modifier: float = 1.0
    accent: str = "neutral"


AVAILABLE_PERSONAS: dict[str, VoicePersona] = {
    "watcher_dm": VoicePersona(
        id="watcher_dm",
        name="The Watcher (Deep Mystical)",
        description="Resonant, deep baritone with subtle cavern reverb for the AI DM.",
        pitch_modifier=0.85,
    ),
    "kyra_stand_in": VoicePersona(
        id="kyra_stand_in",
        name="Kyra Stand-in (Sun Cleric)",
        description="Warm, assertive feminine voice, adaptable with intoxication slurs.",
        pitch_modifier=1.1,
    ),
    "valeros_fighter": VoicePersona(
        id="valeros_fighter",
        name="Valeros (Rugged Fighter)",
        description="Gravelly, confident adventurer cadence.",
        pitch_modifier=0.95,
    ),
}


class DSPApplyRequest(BaseModel):
    filter: str | None = None
    filters: list[str] = Field(default_factory=list)
    audio_base64: str | None = None
    sample_rate: int = 16000
    session_id: str = "session_default"
    speaker_id: str = "speaker_default"
    speaker_name: str = "Unknown"


class DSPApplyResponse(BaseModel):
    audio_base64: str
    audio_payload: str
    audio_bytes_length: int
    audio_stream_url: str = ""
    filters_applied: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    dsp_metadata: dict[str, Any] = Field(default_factory=dict)
    dsp_parameters: dict[str, Any] = Field(default_factory=dict)


class TTSRequest(BaseModel):
    text: str
    persona_id: str = "watcher_dm"
    apply_drunk_filter: bool = False
    filters: list[str] = Field(default_factory=list)
    session_id: str = "session_default"
    speaker_id: str = "speaker_default"
    speaker_name: str = "The Watcher"


class TTSResponse(BaseModel):
    audio_stream_url: str
    duration_ms: int
    persona_used: str
    original_text: str = ""
    conditioned_text: str = ""
    effects_applied: list[str] = Field(default_factory=list)
    dsp_parameters: dict[str, Any] = Field(default_factory=dict)
    dsp_metadata: dict[str, Any] = Field(default_factory=dict)
    audio_payload: str = ""
    audio_base64: str = ""
    latency_ms: float = 0.0


class TranscribeRequest(BaseModel):
    speaker_id: str
    speaker_name: str
    session_id: str
    campaign_id: str
    transcript: str | None = None
    audio_base64: str | None = None
    is_whisper: bool = False
    target_character_id: str | None = None


class TranscribeResponse(BaseModel):
    transcript: str
    speaker_id: str
    speaker_name: str
    event_id: str | None = None
    watcher_intent: dict[str, Any] | None = None
