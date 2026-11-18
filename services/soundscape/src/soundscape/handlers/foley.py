"""Tactical foley triggers and timed audio ducking handler mixin."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.events import DuckingEngaged, DuckingReleased, SoundscapeCueTriggered

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

    def record_ducking_engaged(
        self,
        session_id: str,
        reason: str = "speech",
        duration_ms: int = 0,
        attenuation_db: float = -12.0,
    ) -> None:
        """Record that ducking engages. A positive duration ends the duck when it elapses."""
        self.create_event(
            DuckingEngaged,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            attenuation_db=attenuation_db,
            reason=reason,
            duration_ms=duration_ms,
        )

    def record_ducking_released(self, session_id: str, reason: str = "manual") -> None:
        """Record that ducking releases before its stored duration ends."""
        self.create_event(
            DuckingReleased,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
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

    @handles(DuckingEngaged)
    def _on_ducking_engaged(self, event: DuckingEngaged) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.is_ducked = True
        self.state.ducking_reason = event.reason
        self.state.ducking_attenuation_db = event.attenuation_db
        if event.duration_ms > 0:
            self.state.ducking_until = event.occurred_at + timedelta(milliseconds=event.duration_ms)
        else:
            self.state.ducking_until = None

    @handles(DuckingReleased)
    def _on_ducking_released(self, event: DuckingReleased) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.is_ducked = False
        self.state.ducking_reason = "none"
        self.state.ducking_attenuation_db = 0.0
        self.state.ducking_until = None
