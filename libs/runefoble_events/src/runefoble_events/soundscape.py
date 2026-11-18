"""Soundscape & adaptive audio domain events, powered by eventsource-py."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.soundscape.track_changed")
class SoundscapeTrackChanged(BaseRunefobleEvent):
    """Emitted when active soundscape track or stem profile transitions."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.track_changed"
    session_id: str
    track_id: str
    stem_profile: str  # exploration, tension, combat, boss
    tension_score: int  # 0 to 100
    crossfade_duration_ms: int = 1500
    active_stems: list[str] = Field(default_factory=list)


@register_event("runefoble.events.soundscape.cue_triggered")
class SoundscapeCueTriggered(BaseRunefobleEvent):
    """Emitted when a tactical sound foley or acoustic cue is triggered."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.cue_triggered"
    session_id: str
    cue_id: str
    cue_type: str  # foley, sfx, stinger, ambient
    sound_url: str
    volume_gain: float = 1.0
    duck_music: bool = False


@register_event("runefoble.events.soundscape.tension_updated")
class SoundscapeTensionUpdated(BaseRunefobleEvent):
    """Emitted when encounter tension score is recalculated."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.tension_updated"
    session_id: str
    tension_score: int
    stem_profile: str
    combat_active: bool = False
    combat_round: int = 0
    enemy_cr_balance: float = 0.0
    lowest_health_ratio: float = 1.0


@register_event("runefoble.events.soundscape.party_health_recorded")
class SoundscapePartyHealthRecorded(BaseRunefobleEvent):
    """Emitted when a character's HP ratio changes in a session. Feeds the lowest party health."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.party_health_recorded"
    session_id: str
    character_id: str
    health_ratio: float = Field(ge=0.0, le=1.0)


@register_event("runefoble.events.soundscape.stem_profile_overridden")
class StemProfileOverridden(BaseRunefobleEvent):
    """Emitted when DM forces a stem profile (mood) override."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.stem_profile_overridden"
    session_id: str
    mood: str
    overridden_by: str = "dm"


@register_event("runefoble.events.soundscape.master_volume_changed")
class MasterVolumeChanged(BaseRunefobleEvent):
    """Emitted when the session master volume changes (0.0 to 1.0)."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.master_volume_changed"
    session_id: str
    master_volume: float


@register_event("runefoble.events.soundscape.channel_volume_changed")
class ChannelVolumeChanged(BaseRunefobleEvent):
    """Emitted when the stem channel sliders change. Holds the full channel map after the change."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.channel_volume_changed"
    session_id: str
    channel_volumes: dict[str, float] = Field(default_factory=dict)


@register_event("runefoble.events.soundscape.ducking_engaged")
class DuckingEngaged(BaseRunefobleEvent):
    """Emitted when background audio ducking engages. duration_ms of 0 holds until released."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.ducking_engaged"
    session_id: str
    attenuation_db: float = -12.0
    reason: str = "speech"  # speech, cue, manual
    duration_ms: int = 0


@register_event("runefoble.events.soundscape.ducking_released")
class DuckingReleased(BaseRunefobleEvent):
    """Emitted when background audio ducking is released before any stored duration ends."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.ducking_released"
    session_id: str
    reason: str = "manual"


@register_event("runefoble.events.soundscape.leitmotif_configured")
class LeitmotifProfileConfigured(BaseRunefobleEvent):
    """Emitted when a character's musical leitmotif profile is registered or updated."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.leitmotif_configured"
    session_id: str
    character_id: str
    character_name: str
    instrument_timbre: str  # lute, brass, woodwind, strings, synth
    tempo_multiplier: float = 1.0
    triumphant_stem_url: str
    somber_stem_url: str
    volume_gain: float = 1.0
    attack_ms: int = 150
    release_ms: int = 350
    duration_ms: int = 4000


@register_event("runefoble.events.soundscape.leitmotif_triggered")
class LeitmotifTriggered(BaseRunefobleEvent):
    """Emitted when a character leitmotif stinger is triggered (clutch critical, death save)."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "Soundscape"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.soundscape.leitmotif_triggered"
    session_id: str
    character_id: str
    character_name: str = ""
    playback_id: str = ""
    triggered_at: float = 0.0  # Unix seconds at trigger time
    motif_type: str = "triumphant"  # triumphant, somber, clutch, fanfare
    instrument_timbre: str = "lute"
    stem_url: str
    tempo_multiplier: float = 1.0
    volume_gain: float = 1.0
    attack_ms: int = 150
    release_ms: int = 350
    duration_ms: int = 4000
    duck_music: bool = False
    trigger_reason: str = "critical_hit"  # critical_hit, death_save, audition, manual
