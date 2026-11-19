"""Player speech, Watcher narration, and narrative whisper domain events."""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.watcher.player_spoke")
class PlayerSpokeEvent(BaseRunefobleEvent):
    event_type: str = "runefoble.events.watcher.player_spoke"

    aggregate_type: str = "GameSession"
    speaker_id: str
    speaker_name: str
    transcript: str
    is_whisper: bool = False
    target_character_id: str | None = None


@register_event("runefoble.events.watcher.speech_intent_parsed")
class SpeechIntentParsed(BaseRunefobleEvent):
    event_type: str = "runefoble.events.watcher.speech_intent_parsed"

    aggregate_type: str = "GameSession"
    speaker_name: str
    action_type: str
    target: str | None = None
    confidence: float | None = None
    flavor_text: str = ""
    raw_transcript: str = ""


@register_event("runefoble.events.watcher.stand_in_action_decided")
class StandInActionDecided(BaseRunefobleEvent):
    event_type: str = "runefoble.events.watcher.stand_in_action_decided"

    aggregate_type: str = "GameSession"
    character_name: str
    action_type: str
    dialogue: str
    penalties_applied: list[str] = Field(default_factory=list)
    flavor_text: str = ""


@register_event("runefoble.events.recap.generated")
class AbsenteeRecapGenerated(BaseRunefobleEvent):
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


__all__ = [
    "AbsenteeRecapGenerated",
    "PlayerSpokeEvent",
    "SceneAtmosphereSet",
    "SpeechIntentParsed",
    "StandInActionDecided",
]
