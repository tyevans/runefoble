"""Event-sourced Soundscape aggregate powered by eventsource-py."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from pydantic import BaseModel, Field

from soundscape.handlers import (
    FoleyHandlersMixin,
    LeitmotifHandlersMixin,
    StemHandlersMixin,
    TensionHandlersMixin,
)
from soundscape.mixer import DEFAULT_CHANNEL_VOLUMES, STEM_PROFILE_WEIGHTS, AudioStemMixer


class SoundscapeState(BaseModel):
    """Internal event-sourced state for a soundscape aggregate.

    Every field that a client can read lives here. No process-local cache holds mixer state.
    """

    soundscape_id: UUID = Field(default_factory=uuid4)
    session_id: str = "default"
    current_track_id: str = "track-ambient-01"
    stem_profile: str = "exploration"
    tension_score: int = 10
    active_stems: list[str] = Field(default_factory=lambda: ["ambient"])
    stem_volumes: dict[str, float] = Field(
        default_factory=lambda: STEM_PROFILE_WEIGHTS["exploration"].copy()
    )
    channel_volumes: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_CHANNEL_VOLUMES))
    master_volume: float = 1.0
    is_ducked: bool = False
    ducking_reason: str = "none"
    ducking_attenuation_db: float = -12.0
    # None means a held duck (duration 0) that lasts until a DuckingReleased event.
    ducking_until: datetime | None = None
    manual_override: bool = False
    override_mood: str | None = None
    cues_history: list[dict[str, Any]] = Field(default_factory=list)
    character_profiles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    active_leitmotif: dict[str, Any] | None = None
    leitmotif_history: list[dict[str, Any]] = Field(default_factory=list)
    # Encounter inputs. Set by tension updates, read by round advances and health changes.
    combat_active: bool = False
    combat_round: int = 0
    enemy_cr_balance: float = 0.0
    # Latest HP ratio per character that reported a health change in this session.
    party_health_ratios: dict[str, float] = Field(default_factory=dict)

    @property
    def lowest_party_health_ratio(self) -> float:
        """Lowest HP ratio across the party. A party with no reports reads as full health."""
        return min(self.party_health_ratios.values(), default=1.0)

    def is_ducked_at(self, now: datetime) -> bool:
        """Return True when a duck is engaged and its stored duration has not elapsed."""
        if not self.is_ducked:
            return False
        return self.ducking_until is None or now < self.ducking_until

    def mixer_at(self, now: datetime) -> AudioStemMixer:
        """Build the mixer view for this state at the given instant."""
        return AudioStemMixer(
            stem_profile=self.stem_profile,
            master_volume=self.master_volume,
            is_ducked=self.is_ducked_at(now),
            channel_volumes=self.channel_volumes,
        )


class SoundscapeAggregate(
    StemHandlersMixin,
    FoleyHandlersMixin,
    TensionHandlersMixin,
    LeitmotifHandlersMixin,
    DeclarativeAggregate[SoundscapeState],
):
    """Event-sourced aggregate managing background music stems, tension, and foley cues."""

    aggregate_type = "Soundscape"
    requires_creation_event = False

    @property
    def state(self) -> SoundscapeState:
        """Return the event-sourced state. A stream with no events reads as the default state."""
        return self._state if self._state is not None else self.init_state()

    def init_state(self) -> SoundscapeState:
        return SoundscapeState(soundscape_id=self.aggregate_id)

    def _get_initial_state(self) -> SoundscapeState:
        return self.init_state()
