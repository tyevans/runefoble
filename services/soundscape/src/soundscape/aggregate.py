"""Event-sourced Soundscape aggregate powered by eventsource-py."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.soundscape import (
    SoundscapeCueTriggered,
    SoundscapeDuckingToggled,
    SoundscapeMoodOverridden,
    SoundscapeTensionUpdated,
    SoundscapeTrackChanged,
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


class SoundscapeAggregate(DeclarativeAggregate[SoundscapeState]):
    """Event-sourced aggregate managing background music stems, tension, and foley cues."""

    aggregate_type = "Soundscape"
    requires_creation_event = False

    def init_state(self) -> SoundscapeState:
        return SoundscapeState(soundscape_id=self.aggregate_id)

    def record_track_change(
        self,
        session_id: str,
        track_id: str,
        stem_profile: str,
        tension_score: int,
        crossfade_duration_ms: int = 1500,
        active_stems: list[str] | None = None,
    ) -> None:
        """Record domain state event for track or stem profile transition."""
        self.create_event(
            SoundscapeTrackChanged,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            track_id=track_id,
            stem_profile=stem_profile,
            tension_score=tension_score,
            crossfade_duration_ms=crossfade_duration_ms,
            active_stems=active_stems or [stem_profile],
        )

    def record_cue(
        self,
        session_id: str,
        cue_id: str,
        sound_url: str,
        cue_type: str = "foley",
        volume_gain: float = 1.0,
        duck_music: bool = False,
    ) -> None:
        """Record domain state event for a tactical foley cue."""
        self.create_event(
            SoundscapeCueTriggered,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            cue_id=cue_id,
            cue_type=cue_type,
            sound_url=sound_url,
            volume_gain=volume_gain,
            duck_music=duck_music,
        )

    def record_tension_update(
        self,
        session_id: str,
        tension_score: int,
        stem_profile: str,
        combat_round: int = 0,
        enemy_cr_balance: float = 0.0,
        lowest_health_ratio: float = 1.0,
    ) -> None:
        """Record domain state event for calculated encounter tension score."""
        self.create_event(
            SoundscapeTensionUpdated,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            tension_score=tension_score,
            stem_profile=stem_profile,
            combat_round=combat_round,
            enemy_cr_balance=enemy_cr_balance,
            lowest_health_ratio=lowest_health_ratio,
        )

    def record_mood_override(
        self,
        session_id: str,
        mood: str,
        overridden_by: str = "dm",
    ) -> None:
        """Record domain state event for manual DM mood override."""
        self.create_event(
            SoundscapeMoodOverridden,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            mood=mood,
            overridden_by=overridden_by,
        )

    def record_ducking_toggle(
        self,
        session_id: str,
        is_ducked: bool,
        attenuation_db: float = -12.0,
        reason: str = "speech",
    ) -> None:
        """Record domain state event for WebAudio ducking toggle."""
        self.create_event(
            SoundscapeDuckingToggled,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            is_ducked=is_ducked,
            attenuation_db=attenuation_db,
            reason=reason,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(SoundscapeTrackChanged)
    def _on_track_changed(self, event: SoundscapeTrackChanged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.session_id = event.session_id
        self.state.current_track_id = event.track_id
        self.state.stem_profile = event.stem_profile
        self.state.tension_score = event.tension_score
        self.state.active_stems = event.active_stems
        weights = STEM_PROFILE_WEIGHTS.get(event.stem_profile, STEM_PROFILE_WEIGHTS["exploration"])
        self.state.stem_volumes = weights.copy()

    @handles(SoundscapeCueTriggered)
    def _on_cue_triggered(self, event: SoundscapeCueTriggered) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.cues_history.append(
            {
                "cue_id": event.cue_id,
                "cue_type": event.cue_type,
                "sound_url": event.sound_url,
                "volume_gain": event.volume_gain,
                "duck_music": event.duck_music,
            }
        )
        if len(self.state.cues_history) > 20:
            self.state.cues_history = self.state.cues_history[-20:]

    @handles(SoundscapeTensionUpdated)
    def _on_tension_updated(self, event: SoundscapeTensionUpdated) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.session_id = event.session_id
        self.state.tension_score = event.tension_score
        if not self.state.manual_override:
            self.state.stem_profile = event.stem_profile
            weights = STEM_PROFILE_WEIGHTS.get(
                event.stem_profile, STEM_PROFILE_WEIGHTS["exploration"]
            )
            self.state.stem_volumes = weights.copy()

    @handles(SoundscapeMoodOverridden)
    def _on_mood_overridden(self, event: SoundscapeMoodOverridden) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.manual_override = True
        self.state.override_mood = event.mood
        self.state.stem_profile = event.mood
        weights = STEM_PROFILE_WEIGHTS.get(event.mood, STEM_PROFILE_WEIGHTS["exploration"])
        self.state.stem_volumes = weights.copy()

    @handles(SoundscapeDuckingToggled)
    def _on_ducking_toggled(self, event: SoundscapeDuckingToggled) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.is_ducked = event.is_ducked
        self.state.ducking_attenuation_db = event.attenuation_db
