"""The Watcher, Voice, and Gameplay Stream Events."""

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


@register_event("runefoble.events.dice.rolled")
class DiceRolled(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.dice.rolled"
    session_id: str
    roller_id: str
    roller_name: str
    formula: str
    total: int
    rolls: list[int] = Field(default_factory=list)
    is_crit: bool = False
    is_fumble: bool = False

    @property
    def dice_notation(self) -> str:
        return self.formula

    @property
    def individual_rolls(self) -> list[int]:
        return self.rolls


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


@register_event("runefoble.events.encounter.spawned")
class EncounterSpawned(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Encounter"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.encounter.spawned"
    session_id: str
    encounter_id: str
    encounter_name: str
    threat_level: str
    monsters: list[dict[str, Any]] = Field(default_factory=list)
    tactical_objective: str


@register_event("runefoble.events.encounter.action_resolved")
class AutonomousActionResolved(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Encounter"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.encounter.action_resolved"
    session_id: str
    actor_name: str
    action_type: str
    target_name: str
    narrative: str
    hp_impact: int = 0


@register_event("runefoble.events.voice.audio_conditioned")
class VoiceAudioConditioned(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "VoiceSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.voice.audio_conditioned"
    session_id: str
    speaker_id: str
    speaker_name: str
    filters_applied: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    audio_bytes_length: int = 0


# Legacy backward-compatible aliases
WatcherNarrationEvent = WatcherNarrationGenerated
DiceRollEvent = DiceRolled


@register_event("runefoble.events.watcher.action_proposed")
class WatcherActionProposed(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_proposed"
    action_id: str
    session_id: str
    campaign_id: str = ""
    actor_name: str
    action_type: str
    description: str
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    pause_window_ms: int = 2000


@register_event("runefoble.events.watcher.action_vetoed")
class WatcherActionVetoed(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_vetoed"
    action_id: str
    session_id: str
    campaign_id: str = ""
    vetoed_by: str
    reason: str = ""
    original_action: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.action_approved")
class WatcherActionApproved(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_approved"
    action_id: str
    session_id: str
    campaign_id: str = ""
    approved_by: str
    action_type: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.action_modified")
class WatcherActionModified(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "GameSession"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.action_modified"
    action_id: str
    session_id: str
    campaign_id: str = ""
    modified_by: str
    description: str = ""
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


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
