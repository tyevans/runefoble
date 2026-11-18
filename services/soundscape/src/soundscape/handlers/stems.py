"""Stem crossfading, playback, and volume level handler mixin for Soundscape aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.soundscape import (
    ChannelVolumeChanged,
    MasterVolumeChanged,
    SoundscapeTrackChanged,
)

from soundscape.mixer import STEM_PROFILE_WEIGHTS

if TYPE_CHECKING:
    from soundscape.aggregate import SoundscapeState


class StemHandlersMixin:
    """Mixin providing audio stem playback, crossfade curves, and volume levels."""

    _state: SoundscapeState | None
    state: SoundscapeState
    aggregate_id: Any
    create_event: Any
    init_state: Any

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

    def record_channel_volumes(self, session_id: str, channel_volumes: dict[str, float]) -> None:
        """Record the full stem channel map after a slider change."""
        self.create_event(
            ChannelVolumeChanged,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            channel_volumes=channel_volumes,
        )

    def record_master_volume(self, session_id: str, master_volume: float) -> None:
        """Record a change of the session master volume."""
        self.create_event(
            MasterVolumeChanged,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            master_volume=master_volume,
        )

    @handles(ChannelVolumeChanged)
    def _on_channel_volume_changed(self, event: ChannelVolumeChanged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.channel_volumes = dict(event.channel_volumes)

    @handles(MasterVolumeChanged)
    def _on_master_volume_changed(self, event: MasterVolumeChanged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.master_volume = event.master_volume

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
