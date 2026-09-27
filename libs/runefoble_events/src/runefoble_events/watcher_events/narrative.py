"""Player speech, Watcher narration, and narrative whisper domain events."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class PlayerSpokeEvent(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    speaker_id: str
    speaker_name: str
    transcript: str
    is_whisper: bool = False
    target_character_id: str | None = None


@register_event
class SpeechIntentParsed(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    speaker_name: str
    action_type: str
    target: str | None = None
    confidence: float = 1.0
    flavor_text: str = ""
    raw_transcript: str = ""


@register_event
class WatcherNarrationGenerated(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    narrative_text: str
    tone: str = "dark_fantasy"
    sensory_details: list[str] = Field(default_factory=list)
    suggested_prompts: list[str] = Field(default_factory=list)
    tension_level: str = "rising"


@register_event
class StandInActionDecided(BaseRunefobleEvent):
    aggregate_type: str = "GameSession"
    character_name: str
    action_type: str
    dialogue: str
    penalties_applied: list[str] = Field(default_factory=list)
    flavor_text: str = ""


StandInTurnExecuted = StandInActionDecided
WatcherNarrationEvent = WatcherNarrationGenerated


@register_event("runefoble.events.recap.generated")
class AbsenteeRecapGenerated(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Chronicle"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.recap.generated"
    session_id: str
    character_id: str
    character_name: str
    stand_in_persona: str
    penalties: list[str] = Field(default_factory=list)
    narrative_summary: str
    highlights: list[str] = Field(default_factory=list)
    audio_url: str | None = None
    hp_delta: int = 0
    items_acquired: list[str] = Field(default_factory=list)


@register_event("runefoble.events.scene.atmosphere_set")
class SceneAtmosphereSet(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Scene"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.scene.atmosphere_set"
    session_id: str
    scene_id: str
    location_name: str
    lighting: str
    mood: str
    description: str
    ambient_audio_prompt: str


@register_event("runefoble.events.watcher.narrative_whispered")
class DMNarrativeWhispered(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.narrative_whispered"
    whisper_id: str
    session_id: str
    campaign_id: str = ""
    whisper_type: str = "atmospheric_hint"
    content: str
    recipient_role: str = "dungeon_master"
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "AbsenteeRecapGenerated",
    "DMNarrativeWhispered",
    "PlayerSpokeEvent",
    "SceneAtmosphereSet",
    "SpeechIntentParsed",
    "StandInActionDecided",
    "StandInTurnExecuted",
    "WatcherNarrationEvent",
    "WatcherNarrationGenerated",
]
