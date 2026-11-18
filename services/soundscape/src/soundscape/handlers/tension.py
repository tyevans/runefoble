"""Encounter tension scoring and dynamic musical mood scaling handler mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eventsource.domain.decorators import handles
from runefoble_events.soundscape import (
    SoundscapePartyHealthRecorded,
    SoundscapeTensionUpdated,
    StemProfileOverridden,
)

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
        combat_active: bool = False,
    ) -> None:
        """Record domain state event for calculated encounter tension score."""
        self.create_event(
            SoundscapeTensionUpdated,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            tension_score=tension_score,
            stem_profile=stem_profile,
            combat_active=combat_active,
            combat_round=combat_round,
            enemy_cr_balance=enemy_cr_balance,
            lowest_health_ratio=lowest_health_ratio,
        )

    def record_party_health(self, session_id: str, character_id: str, health_ratio: float) -> None:
        """Record domain state event for one character's HP ratio (current HP / max HP)."""
        self.create_event(
            SoundscapePartyHealthRecorded,
            aggregate_id=self.aggregate_id,
            session_id=session_id,
            character_id=character_id,
            health_ratio=health_ratio,
        )

    def record_stem_profile_overridden(
        self,
        session_id: str,
        mood: str,
        overridden_by: str = "dm",
    ) -> None:
        """Record domain state event for a manual DM stem profile override."""
        self.create_event(
            StemProfileOverridden,
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
        self.state.combat_active = event.combat_active
        self.state.combat_round = event.combat_round
        self.state.enemy_cr_balance = event.enemy_cr_balance
        if not self.state.manual_override:
            self.state.stem_profile = event.stem_profile
            weights = STEM_PROFILE_WEIGHTS.get(
                event.stem_profile, STEM_PROFILE_WEIGHTS["exploration"]
            )
            self.state.stem_volumes = weights.copy()

    @handles(SoundscapePartyHealthRecorded)
    def _on_party_health_recorded(self, event: SoundscapePartyHealthRecorded) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.party_health_ratios[event.character_id] = event.health_ratio

    @handles(StemProfileOverridden)
    def _on_stem_profile_overridden(self, event: StemProfileOverridden) -> None:
        if self._state is None:
            self._state = self.init_state()
        self.state.manual_override = True
        self.state.override_mood = event.mood
        self.state.stem_profile = event.mood
        weights = STEM_PROFILE_WEIGHTS.get(event.mood, STEM_PROFILE_WEIGHTS["exploration"])
        self.state.stem_volumes = weights.copy()
