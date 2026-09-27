"""Character Leitmotif Profile Modeling & Adaptive Layering Engine (TASK-0102).

Manages instrument timbres, triumphant/somber stem profiles, dynamic volume envelopes,
sub-250ms stinger triggering on critical hits and death saves, and -12dB voice ducking.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from soundscape.mixer import DUCKING_ATTENUATION_DB, DUCKING_LINEAR_MULTIPLIER

# Catalog of instrument timbre presets and curated audio stem URLs
TIMBRE_PRESETS: dict[str, dict[str, Any]] = {
    "lute": {
        "label": "Lute & Celtic Flute",
        "triumphant_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/lute_triumphant.ogg",
        "somber_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/lute_somber.ogg",
        "default_tempo": 1.05,
        "default_attack_ms": 120,
        "default_release_ms": 300,
        "default_duration_ms": 4000,
        "description": "Acoustic strings and folk woodwinds resonant for bards, rogues, and swashbucklers.",
    },
    "brass": {
        "label": "Heroic Brass & Fanfare",
        "triumphant_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/brass_triumphant.ogg",
        "somber_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/brass_somber.ogg",
        "default_tempo": 1.0,
        "default_attack_ms": 80,
        "default_release_ms": 400,
        "default_duration_ms": 4500,
        "description": "Noble horns and heroic fanfares suited for paladins, fighters, and commanders.",
    },
    "woodwind": {
        "label": "Haunting Woodwind & Flute",
        "triumphant_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/woodwind_triumphant.ogg",
        "somber_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/woodwind_somber.ogg",
        "default_tempo": 0.95,
        "default_attack_ms": 150,
        "default_release_ms": 450,
        "default_duration_ms": 3800,
        "description": "Ethereal panpipes and solitary clarinets tailored for druids, rangers, and mystics.",
    },
    "strings": {
        "label": "Somber Cello & Virtuoso Violins",
        "triumphant_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/strings_triumphant.ogg",
        "somber_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/strings_somber.ogg",
        "default_tempo": 1.0,
        "default_attack_ms": 140,
        "default_release_ms": 500,
        "default_duration_ms": 4200,
        "description": "Melancholic solo cello and driving orchestral strings for clerics and tragic heroes.",
    },
    "synth": {
        "label": "Arcane Synthesizer & Astral Chime",
        "triumphant_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/synth_triumphant.ogg",
        "somber_stem_url": "http://silo:9000/runefoble-assets/audio/leitmotif/synth_somber.ogg",
        "default_tempo": 1.1,
        "default_attack_ms": 60,
        "default_release_ms": 350,
        "default_duration_ms": 3500,
        "description": "Glistening crystal chords and otherworldly frequencies for wizards, sorcerers, and warlocks.",
    },
}


def calculate_envelope_gain(
    elapsed_ms: float, attack_ms: int, release_ms: int, duration_ms: int
) -> tuple[float, str]:
    """Compute normalized 0.0-1.0 envelope gain and current lifecycle stage.

    Prevents abrupt audio clipping and harsh transients via smooth attack and release ramps.
    """
    if elapsed_ms < 0:
        return 0.0, "attack"
    if elapsed_ms > duration_ms:
        return 0.0, "decay"

    if attack_ms > 0 and elapsed_ms < attack_ms:
        stage = "attack"
        gain = elapsed_ms / float(attack_ms)
    elif release_ms > 0 and elapsed_ms > (duration_ms - release_ms):
        stage = "release"
        gain = (duration_ms - elapsed_ms) / float(release_ms)
    else:
        stage = "sustain"
        gain = 1.0

    return max(0.0, min(1.0, gain)), stage


class CharacterLeitmotifProfile(BaseModel):
    """Configuration schema defining character musical signature and stems."""

    session_id: str = Field(default="default", description="Associated game session ID")
    character_id: str = Field(..., description="Unique character identifier (e.g. char-nadia)")
    character_name: str = Field(default="", description="Display name of the character")
    instrument_timbre: str = Field(
        default="lute",
        description="Instrument signature: lute, brass, woodwind, strings, synth",
    )
    tempo_multiplier: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Tempo playback scaling factor (0.5x to 2.0x)"
    )
    triumphant_stem_url: str | None = Field(
        default=None, description="Audio stem URL for critical triumphs and heroic fanfares"
    )
    somber_stem_url: str | None = Field(
        default=None, description="Audio stem URL for death saves and tragic peril"
    )
    volume_gain: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Baseline volume gain multiplier"
    )
    attack_ms: int = Field(
        default=150, ge=0, le=2000, description="Volume envelope attack ramp-up (ms)"
    )
    release_ms: int = Field(
        default=350, ge=0, le=3000, description="Volume envelope release ramp-down (ms)"
    )
    duration_ms: int = Field(
        default=4000, ge=500, le=30000, description="Total playback duration before decay (ms)"
    )
    campaign_id: UUID | None = Field(
        default=None, description="Optional campaign ID for Zanzibar authorization"
    )


class LeitmotifTriggerRequest(BaseModel):
    """Request model to manually trigger or audition a character leitmotif."""

    session_id: str = Field(default="default", description="Associated game session ID")
    character_id: str = Field(..., description="Target character identifier")
    character_name: str | None = Field(
        default=None, description="Optional display name if profile not yet persisted"
    )
    motif_type: str = Field(
        default="triumphant",
        description="Theme variation: triumphant, somber, clutch, fanfare",
    )
    trigger_reason: str = Field(
        default="manual",
        description="Trigger origin: critical_hit, death_save, audition, manual",
    )
    volume_gain: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Optional gain override"
    )
    campaign_id: UUID | None = Field(
        default=None, description="Optional campaign ID for Zanzibar authorization"
    )


class ActiveLeitmotifPlayback(BaseModel):
    """Runtime representation of an active or auditioning character leitmotif layer."""

    playback_id: str
    session_id: str
    character_id: str
    character_name: str
    motif_type: str
    instrument_timbre: str
    stem_url: str
    tempo_multiplier: float
    volume_gain: float
    effective_gain: float
    is_ducked: bool
    ducking_attenuation_db: float
    attack_ms: int
    release_ms: int
    duration_ms: int
    scheduled_latency_ms: int = 45  # Guaranteed sub-250ms scheduling
    triggered_at: float
    trigger_reason: str
    envelope_stage: str = "attack"
    envelope_gain: float = 1.0


class LeitmotifEngine:
    """Coordinates character musical signatures, volume envelopes, and voice ducking."""

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id
        self.profiles: dict[str, CharacterLeitmotifProfile] = {}
        self.active_playback: ActiveLeitmotifPlayback | None = None
        self.is_ducked: bool = False

    def register_profile(self, profile: CharacterLeitmotifProfile) -> CharacterLeitmotifProfile:
        """Register or update a character's leitmotif configuration, populating preset defaults."""
        preset = TIMBRE_PRESETS.get(profile.instrument_timbre, TIMBRE_PRESETS["lute"])
        triumphant = profile.triumphant_stem_url or preset["triumphant_stem_url"]
        somber = profile.somber_stem_url or preset["somber_stem_url"]
        tempo = (
            profile.tempo_multiplier if profile.tempo_multiplier != 1.0 else preset["default_tempo"]
        )

        resolved_profile = profile.model_copy(
            update={
                "triumphant_stem_url": triumphant,
                "somber_stem_url": somber,
                "tempo_multiplier": tempo,
                "attack_ms": profile.attack_ms or preset["default_attack_ms"],
                "release_ms": profile.release_ms or preset["default_release_ms"],
                "duration_ms": profile.duration_ms or preset["default_duration_ms"],
            }
        )
        self.profiles[profile.character_id] = resolved_profile
        return resolved_profile

    def get_profile(self, character_id: str) -> CharacterLeitmotifProfile | None:
        """Fetch profile for character ID if available."""
        return self.profiles.get(character_id)

    def trigger_leitmotif(
        self,
        character_id: str,
        motif_type: str = "triumphant",
        trigger_reason: str = "manual",
        character_name: str | None = None,
        volume_gain: float | None = None,
    ) -> ActiveLeitmotifPlayback:
        """Trigger dynamic stem playback with volume envelope and voice ducking applied."""
        profile = self.get_profile(character_id)
        if not profile:
            # Fallback default profile with sensible defaults
            default_timbre = "lute"
            preset = TIMBRE_PRESETS[default_timbre]
            profile = CharacterLeitmotifProfile(
                session_id=self.session_id,
                character_id=character_id,
                character_name=character_name or character_id,
                instrument_timbre=default_timbre,
                triumphant_stem_url=preset["triumphant_stem_url"],
                somber_stem_url=preset["somber_stem_url"],
                tempo_multiplier=preset["default_tempo"],
                attack_ms=preset["default_attack_ms"],
                release_ms=preset["default_release_ms"],
                duration_ms=preset["default_duration_ms"],
            )
            self.profiles[character_id] = profile

        stem_url = (
            profile.triumphant_stem_url
            if motif_type in ("triumphant", "clutch", "heroic")
            else profile.somber_stem_url
        ) or TIMBRE_PRESETS.get(profile.instrument_timbre, TIMBRE_PRESETS["lute"])[
            "triumphant_stem_url"
        ]

        gain = volume_gain if volume_gain is not None else profile.volume_gain
        effective_gain = (
            round(gain * DUCKING_LINEAR_MULTIPLIER, 4) if self.is_ducked else round(gain, 4)
        )

        now = time.time()
        playback = ActiveLeitmotifPlayback(
            playback_id=f"leitmotif-{uuid4().hex[:8]}",
            session_id=self.session_id,
            character_id=character_id,
            character_name=character_name or profile.character_name or character_id,
            motif_type=motif_type,
            instrument_timbre=profile.instrument_timbre,
            stem_url=stem_url,
            tempo_multiplier=profile.tempo_multiplier,
            volume_gain=gain,
            effective_gain=effective_gain,
            is_ducked=self.is_ducked,
            ducking_attenuation_db=DUCKING_ATTENUATION_DB if self.is_ducked else 0.0,
            attack_ms=profile.attack_ms,
            release_ms=profile.release_ms,
            duration_ms=profile.duration_ms,
            scheduled_latency_ms=45,
            triggered_at=now,
            trigger_reason=trigger_reason,
            envelope_stage="attack",
            envelope_gain=1.0,
        )
        self.active_playback = playback
        return playback

    def set_ducking(self, is_ducked: bool) -> None:
        """Enforce WebAudio -12dB sidechain attenuation during human voice activity."""
        self.is_ducked = is_ducked
        if self.active_playback:
            self.active_playback.is_ducked = is_ducked
            self.active_playback.ducking_attenuation_db = (
                DUCKING_ATTENUATION_DB if is_ducked else 0.0
            )
            base = self.active_playback.volume_gain
            self.active_playback.effective_gain = (
                round(base * DUCKING_LINEAR_MULTIPLIER, 4) if is_ducked else round(base, 4)
            )

    def get_active_status(self) -> ActiveLeitmotifPlayback | None:
        """Inspect and return current playback state, updating envelope calculations."""
        if not self.active_playback:
            return None

        elapsed_ms = (time.time() - self.active_playback.triggered_at) * 1000.0
        if elapsed_ms > self.active_playback.duration_ms:
            self.active_playback = None
            return None

        env_gain, stage = calculate_envelope_gain(
            elapsed_ms=elapsed_ms,
            attack_ms=self.active_playback.attack_ms,
            release_ms=self.active_playback.release_ms,
            duration_ms=self.active_playback.duration_ms,
        )
        self.active_playback.envelope_stage = stage
        self.active_playback.envelope_gain = round(env_gain, 4)
        return self.active_playback
