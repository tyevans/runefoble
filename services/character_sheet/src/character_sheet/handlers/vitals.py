"""Vitals, condition states, absence penalties, and stand-in policy handlers."""

from typing import Any, Literal

from character_sheet.models import CharacterState, StandInGuardrails
from eventsource.domain.decorators import handles
from runefoble_events import events as ev

PenaltyType = Literal["drunk", "foolishness", "cowardice", "greed", "curse"]
ImposedBy = Literal["human_dm", "the_watcher"]


class VitalsHandlerMixin:
    """Mixin providing HP mutations, conditions, absence penalties, and stand-in guardrails."""

    _state: CharacterState | None
    state: CharacterState
    create_event: Any
    aggregate_id: Any

    def _emit_hp(self, delta: int, hp: int, src: str) -> None:
        kw = {"delta": delta, "current_hp": hp, "max_hp": self.state.max_hp, "source": src}
        if delta < 0:
            self.create_event(ev.CharacterDamaged, character_id=str(self.aggregate_id), **kw)
        self.create_event(ev.CharacterHealthChanged, **kw)

    def modify_health(
        self, delta: int, source: str = "damage", is_stand_in: bool | None = None
    ) -> None:
        """Apply damage or healing with zero-HP permadeath safeguard for stand-ins."""
        effective_stand_in = (
            is_stand_in if is_stand_in is not None else self.state.is_stand_in_active
        )
        if (
            delta < 0
            and (self.state.current_hp + delta <= 0)
            and effective_stand_in
            and self.state.stand_in_guardrails.permadeath_safeguard
        ):
            self._emit_hp(delta, 0, source)
            self.create_event(
                ev.StandInStabilized,
                character_id=str(self.aggregate_id),
                current_hp=0,
                condition="unconscious_stabilized",
            )
            self.create_event(
                ev.ConditionApplied,
                condition="unconscious_stabilized",
                duration_rounds=None,
                source="permadeath_safeguard",
            )
            return

        new_hp = max(0, min(self.state.max_hp, self.state.current_hp + delta))
        self._emit_hp(delta, new_hp, source)

    def update_stand_in_guardrails(self, guardrails: StandInGuardrails | dict[str, Any]) -> None:
        """Configure tactical constraints for stand-in AI."""
        gr = guardrails.model_dump() if hasattr(guardrails, "model_dump") else dict(guardrails)
        self.create_event(
            ev.StandInPolicyUpdated, character_id=str(self.aggregate_id), guardrails=gr
        )

    def set_stand_in_active(self, active: bool) -> None:
        self._state = self.state.with_stand_in_active(active)

    def apply_penalty(
        self, penalty_type: PenaltyType, description: str, imposed_by: ImposedBy = "the_watcher"
    ) -> None:
        """Apply a session miss penalty to an absent player's character."""
        self.create_event(
            ev.AbsencePenaltyApplied,
            penalty_type=penalty_type,
            description=description,
            imposed_by=imposed_by,
        )

    def clear_penalty(self, penalty_type: str) -> None:
        """Clear an active penalty once the player returns or redeems themselves."""
        if penalty_type.lower() not in self.state.penalties:
            raise ValueError(f"Penalty '{penalty_type}' is not active on this character")
        self.create_event(ev.AbsencePenaltyCleared, penalty_type=penalty_type.lower())

    def apply_condition(
        self, condition: str, duration_rounds: int | None = None, source: str = ""
    ) -> None:
        """Inflict an active gameplay condition (e.g. 'blinded', 'prone', 'poisoned')."""
        self.create_event(
            ev.ConditionApplied,
            condition=condition.lower(),
            duration_rounds=duration_rounds,
            source=source,
        )

    def remove_condition(self, condition: str) -> None:
        """Remove a status condition from the character."""
        cond = condition.lower()
        if cond not in self.state.conditions:
            raise ValueError(f"Condition '{condition}' is not active on this character")
        self.create_event(ev.ConditionRemoved, condition=cond)

    @handles(ev.CharacterHealthChanged)
    def _on_health_changed(self, event: ev.CharacterHealthChanged) -> None:
        self._state = self.state.with_health(event.current_hp)

    @handles(ev.AbsencePenaltyApplied)
    def _on_penalty_applied(self, event: ev.AbsencePenaltyApplied) -> None:
        self._state = self.state.with_penalty(event.penalty_type, event.description)

    @handles(ev.AbsencePenaltyCleared)
    def _on_penalty_cleared(self, event: ev.AbsencePenaltyCleared) -> None:
        self._state = self.state.without_penalty(event.penalty_type)

    @handles(ev.ConditionApplied)
    def _on_condition_applied(self, event: ev.ConditionApplied) -> None:
        self._state = self.state.with_condition(
            event.condition, event.duration_rounds, event.source
        )

    @handles(ev.ConditionRemoved)
    def _on_condition_removed(self, event: ev.ConditionRemoved) -> None:
        self._state = self.state.without_condition(event.condition)

    @handles(ev.StandInPolicyUpdated)
    def _on_guardrails_updated(self, event: ev.StandInPolicyUpdated) -> None:
        self._state = self.state.with_stand_in_guardrails(event.guardrails)

    @handles(ev.StandInStabilized)
    def _on_stand_in_stabilized(self, event: ev.StandInStabilized) -> None:
        self._state = self.state.with_stabilized()
