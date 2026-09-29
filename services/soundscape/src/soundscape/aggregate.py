"""Event-sourced Soundscape aggregate powered by eventsource-py."""

from __future__ import annotations

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
from soundscape.mixer import STEM_PROFILE_WEIGHTS


class SoundscapeState(BaseModel):
    """Internal event-sourced state for a soundscape aggregate."""

    soundscape_id: UUID = Field(default_factory=uuid4)
    session_id: str = "default"
    current_track_id: str = "track-ambient-01"
    stem_profile: str = "exploration"
    tension_score: int = 10
    active_stems: list[str] = Field(default_factory=lambda: ["ambient"])
    stem_volumes: dict[str, float] = Field(
        default_factory=lambda: STEM_PROFILE_WEIGHTS["exploration"].copy()
    )
    master_volume: float = 1.0
    is_ducked: bool = False
    ducking_attenuation_db: float = -12.0
    manual_override: bool = False
    override_mood: str | None = None
    cues_history: list[dict[str, Any]] = Field(default_factory=list)
    character_profiles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    active_leitmotif: dict[str, Any] | None = None
    leitmotif_history: list[dict[str, Any]] = Field(default_factory=list)


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

    def init_state(self) -> SoundscapeState:
        return SoundscapeState(soundscape_id=self.aggregate_id)

    def _get_initial_state(self) -> SoundscapeState:
        return self.init_state()
