"""Character leitmotif profile and reactive trigger handler mixin for Soundscape aggregate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.soundscape import (
    LeitmotifProfileConfigured,
    LeitmotifTriggered,
)

if TYPE_CHECKING:
    from soundscape.aggregate import SoundscapeState


class LeitmotifHandlersMixin:
    """Mixin providing character leitmotif configuration and reactive playback triggers."""

    _state: SoundscapeState | None
    state: SoundscapeState
    aggregate_id: Any
    create_event: Any
    init_state: Any

    def record_leitmotif_profile(
        self,
        session_id: str,
        character_id: str,
        character_name: str,
        instrument_timbre: str,
        tempo_multiplier: float = 1.0,
        triumphant_stem_url: str = "",
        somber_stem_url: str = "",
        volume_gain: float = 1.0,
        attack_ms: int = 150,
        release_ms: int = 350,
        duration_ms: int = 4000,
    ) -> None:
        """Record domain state event for character leitmotif profile registration."""
        self.create_event(
            LeitmotifProfileConfigured,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            character_id=character_id,
            character_name=character_name,
            instrument_timbre=instrument_timbre,
            tempo_multiplier=tempo_multiplier,
            triumphant_stem_url=triumphant_stem_url,
            somber_stem_url=somber_stem_url,
            volume_gain=volume_gain,
            attack_ms=attack_ms,
            release_ms=release_ms,
            duration_ms=duration_ms,
        )

    def record_leitmotif_trigger(
        self,
        session_id: str,
        character_id: str,
        character_name: str = "",
        motif_type: str = "triumphant",
        instrument_timbre: str = "lute",
        stem_url: str = "",
        tempo_multiplier: float = 1.0,
        volume_gain: float = 1.0,
        attack_ms: int = 150,
        release_ms: int = 350,
        duration_ms: int = 4000,
        duck_music: bool = False,
        trigger_reason: str = "critical_hit",
    ) -> None:
        """Record domain state event for character leitmotif trigger."""
        self.create_event(
            LeitmotifTriggered,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            character_id=character_id,
            character_name=character_name,
            motif_type=motif_type,
            instrument_timbre=instrument_timbre,
            stem_url=stem_url,
            tempo_multiplier=tempo_multiplier,
            volume_gain=volume_gain,
            attack_ms=attack_ms,
            release_ms=release_ms,
            duration_ms=duration_ms,
            duck_music=duck_music,
            trigger_reason=trigger_reason,
        )

    @handles(LeitmotifProfileConfigured)
    def _on_leitmotif_configured(self, event: LeitmotifProfileConfigured) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.character_profiles[event.character_id] = {
            "session_id": event.session_id,
            "character_id": event.character_id,
            "character_name": event.character_name,
            "instrument_timbre": event.instrument_timbre,
            "tempo_multiplier": event.tempo_multiplier,
            "triumphant_stem_url": event.triumphant_stem_url,
            "somber_stem_url": event.somber_stem_url,
            "volume_gain": event.volume_gain,
            "attack_ms": event.attack_ms,
            "release_ms": event.release_ms,
            "duration_ms": event.duration_ms,
        }

    @handles(LeitmotifTriggered)
    def _on_leitmotif_triggered(self, event: LeitmotifTriggered) -> None:
        if self._state is None:
            self._state = self.init_state()
        motif_data = {
            "session_id": event.session_id,
            "character_id": event.character_id,
            "character_name": event.character_name,
            "motif_type": event.motif_type,
            "instrument_timbre": event.instrument_timbre,
            "stem_url": event.stem_url,
            "tempo_multiplier": event.tempo_multiplier,
            "volume_gain": event.volume_gain,
            "attack_ms": event.attack_ms,
            "release_ms": event.release_ms,
            "duration_ms": event.duration_ms,
            "duck_music": event.duck_music,
            "trigger_reason": event.trigger_reason,
        }
        self.state.active_leitmotif = motif_data
        self.state.leitmotif_history.append(motif_data)
        if len(self.state.leitmotif_history) > 20:
            self.state.leitmotif_history = self.state.leitmotif_history[-20:]
