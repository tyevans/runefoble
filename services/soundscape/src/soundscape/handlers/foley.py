"""Tactical foley triggers, acoustic positioning, and audio ducking handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.soundscape import SoundscapeCueTriggered, SoundscapeDuckingToggled

if TYPE_CHECKING:
    from soundscape.aggregate import SoundscapeState


class FoleyHandlersMixin:
    """Mixin providing tactical foley triggers and audio ducking control."""

    _state: SoundscapeState | None
    state: SoundscapeState
    aggregate_id: Any
    create_event: Any
    init_state: Any

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

    @handles(SoundscapeDuckingToggled)
    def _on_ducking_toggled(self, event: SoundscapeDuckingToggled) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.is_ducked = event.is_ducked
        self.state.ducking_attenuation_db = event.attenuation_db
