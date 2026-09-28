"""Condition states, condition modifiers, and absence penalty models."""

from __future__ import annotations

from typing import Any, Literal

from character_sheet.portrait import compute_condition_badges, resolve_active_portrait_url
from pydantic import BaseModel, Field


class ConditionState(BaseModel):
    condition: str
    duration_rounds: int | None = None
    source: str = ""


class ConditionModifier(BaseModel):
    condition: str
    effect_type: Literal["tactical", "absence_penalty", "spell", "environmental"] = "tactical"
    description: str = ""
    disadvantage_checks: list[str] = Field(default_factory=list)
    speed_penalty_ft: int = 0
    saving_throw_modifier: str = ""


class ConditionsTransitionsMixin:
    """Transition methods for tactical conditions, penalties, and zero-HP stabilization."""

    def with_penalty(self: Any, penalty_type: str, description: str) -> Any:
        pens = dict(self.penalties)
        pens[penalty_type.lower()] = description
        return self.model_copy(update={"penalties": pens})

    def without_penalty(self: Any, penalty_type: str) -> Any:
        pens = dict(self.penalties)
        pens.pop(penalty_type.lower(), None)
        return self.model_copy(update={"penalties": pens})

    def with_condition(self: Any, condition: str, duration_rounds: int | None, source: str) -> Any:
        conds = dict(self.conditions)
        conds[condition] = ConditionState(
            condition=condition, duration_rounds=duration_rounds, source=source
        )
        badges = compute_condition_badges(self.current_hp, self.max_hp, conds)
        active_url = resolve_active_portrait_url(
            self.base_portrait_url, self.current_hp, self.max_hp, conds
        )
        return self.model_copy(
            update={
                "conditions": conds,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )

    def without_condition(self: Any, condition: str) -> Any:
        conds = dict(self.conditions)
        conds.pop(condition, None)
        badges = compute_condition_badges(self.current_hp, self.max_hp, conds)
        active_url = resolve_active_portrait_url(
            self.base_portrait_url, self.current_hp, self.max_hp, conds
        )
        return self.model_copy(
            update={
                "conditions": conds,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )

    def with_stabilized(self: Any) -> Any:
        conds = dict(self.conditions)
        conds["unconscious_stabilized"] = ConditionState(
            condition="unconscious_stabilized",
            duration_rounds=None,
            source="permadeath_safeguard",
        )
        badges = compute_condition_badges(0, self.max_hp, conds)
        active_url = resolve_active_portrait_url(self.base_portrait_url, 0, self.max_hp, conds)
        return self.model_copy(
            update={
                "current_hp": 0,
                "is_stabilized": True,
                "conditions": conds,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )
