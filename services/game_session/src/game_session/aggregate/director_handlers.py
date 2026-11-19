"""DM override and atmosphere domain handler mixin for the GameSession aggregate."""

from __future__ import annotations

from typing import Any

from eventsource.domain.decorators import handles
from game_session.models import GameSessionState
from runefoble_events.events import AtmosphereUpdated, DMOverrideApplied, WeatherChanged


class DirectorHandlersMixin:
    """Records DM overrides and atmosphere changes on the session aggregate."""

    _state: GameSessionState | None
    state: GameSessionState
    aggregate_id: Any
    create_event: Any

    def apply_dm_override(self, action: str, reason: str | None, payload: dict[str, Any]) -> None:
        """Record a DM override on the session."""
        self.create_event(
            DMOverrideApplied,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            action=action,
            reason=reason,
            payload=payload,
        )

    def update_atmosphere(
        self,
        location_name: str,
        lighting: str,
        mood: str,
        description: str,
        ambient_audio_prompt: str | None,
    ) -> None:
        """Record a change of location, lighting, and mood."""
        self.create_event(
            AtmosphereUpdated,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            location_name=location_name,
            lighting=lighting,
            mood=mood,
            description=description,
            ambient_audio_prompt=ambient_audio_prompt,
        )

    def apply_weather(self, weather: str, source_proposal_id: str | None) -> None:
        """Record a weather change from an approved audience modifier."""
        self.create_event(
            WeatherChanged,
            campaign_id=self.state.campaign_id,
            session_id=self.aggregate_id,
            weather=weather,
            source_proposal_id=source_proposal_id,
        )

    @handles(WeatherChanged)
    def _on_weather_changed(self, event: WeatherChanged) -> None:
        self._state = self.state.with_weather(
            event.weather, str(event.source_proposal_id) if event.source_proposal_id else None
        )

    @handles(DMOverrideApplied)
    def _on_dm_override_applied(self, event: DMOverrideApplied) -> None:
        self._state = self.state.with_dm_override(event.action, event.reason, event.payload)

    @handles(AtmosphereUpdated)
    def _on_atmosphere_updated(self, event: AtmosphereUpdated) -> None:
        self._state = self.state.with_atmosphere(
            {
                "location_name": event.location_name,
                "lighting": event.lighting,
                "mood": event.mood,
                "description": event.description,
                "ambient_audio_prompt": event.ambient_audio_prompt,
            }
        )
