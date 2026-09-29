"""Encounter tension scoring and dynamic musical mood scaling handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.soundscape import SoundscapeMoodOverridden, SoundscapeTensionUpdated

from soundscape.mixer import STEM_PROFILE_WEIGHTS

if TYPE_CHECKING:
    from soundscape.aggregate import SoundscapeState


class TensionHandlersMixin:
    """Mixin providing encounter tension scoring and dynamic mood scaling."""

    _state: SoundscapeState | None
    state: SoundscapeState
    aggregate_id: Any
    create_event: Any
    init_state: Any

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
