"""Alchemical crafting execution engine and event-sourced aggregate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from character_sheet.crafting.mishaps import MishapResolver, calculate_volatile_risk
from character_sheet.crafting.recipes import (
    CraftingAttemptRecord,
    CraftingState,
    find_matching_recipe,
)
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.events import CraftingAttempted, CraftingMishapOccurred, CraftingSucceeded
from runefoble_platform.identifiers import opaque_optional_aggregate_id


@dataclass(frozen=True)
class CombineOutcome:
    """Typed result of one reagent combination. A mishap carries its mishap record."""

    outcome: Literal["success", "mishap"]
    risk_score: float
    item_name: str | None = None
    recipe_name: str | None = None
    quantity: int = 1
    tags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    reagents_consumed: list[str] = field(default_factory=list)
    catalyst_consumed: str | None = None
    mishap: dict[str, Any] | None = None


class CraftingEngine:
    """Orchestrator for crafting attempt resolution and proficiency bonuses."""

    @staticmethod
    def apply_proficiency(base: int, bonus: int = 0) -> int:
        return base + bonus

    @staticmethod
    def evaluate_recipe(reagents: list[str]) -> tuple[str, str, list[str], dict[str, Any]]:
        if matched := find_matching_recipe(reagents):
            return matched["name"], matched["name"], matched["tags"], matched["properties"]
        return (
            f"Experimental Brew ({' & '.join(reagents)})",
            "Experimental Alchemy",
            ["consumable", "experimental", "alchemy"],
            {"potency": 2, "description": "A novel alchemical concoction."},
        )

    @classmethod
    def resolve(
        cls,
        cid: UUID,
        reagents: list[str],
        cat: str | None,
        camp: UUID | None,
        sess: UUID | None,
        pid: str | None,
        force_mishap: bool,
        thresh: float,
    ) -> tuple[dict[str, Any], type, dict[str, Any], CombineOutcome]:
        risk = calculate_volatile_risk(reagents, cat)
        att = {"character_id": cid, "player_id": pid, "campaign_id": camp}
        att.update(session_id=sess, reagents=reagents, catalyst=cat, risk_score=risk)
        if MishapResolver.is_mishap(risk, cat, force_mishap, thresh):
            mishap = MishapResolver.select_mishap(risk)
            m_kw = MishapResolver.event_kwargs(cid, mishap, reagents, camp, sess)
            return (
                att,
                CraftingMishapOccurred,
                m_kw,
                CombineOutcome(outcome="mishap", risk_score=risk, mishap=mishap),
            )

        item, rec, tags, props = cls.evaluate_recipe(reagents)
        s_kw: dict[str, Any] = {
            "item_name": item,
            "recipe_name": rec,
            "quantity": 1,
            "tags": tags,
            "properties": props,
            "reagents_consumed": reagents,
            "catalyst_consumed": cat,
            "character_id": cid,
            "campaign_id": camp,
            "session_id": sess,
        }
        outcome = CombineOutcome(
            outcome="success",
            risk_score=risk,
            item_name=item,
            recipe_name=rec,
            quantity=1,
            tags=tags,
            properties=props,
            reagents_consumed=reagents,
            catalyst_consumed=cat,
        )
        return att, CraftingSucceeded, s_kw, outcome


class CraftingAggregate(DeclarativeAggregate[CraftingState]):
    """Event-sourced aggregate managing alchemical experimentation and volatile risk.

    The aggregate records each combine decision and its outcome. The character applies the
    recorded outcome later through the crafting process manager (TASK-0772).
    """

    aggregate_type = "Crafting"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        self._state = self._state or CraftingState(character_id=aggregate_id)

    @handles(CraftingAttempted)
    def handle_attempted(self, e: CraftingAttempted) -> None:
        self._state = self._state or CraftingState(character_id=e.character_id)
        self.state.character_id = e.character_id
        self.state.total_crafts += 1
        st = self.state
        st.attempts.append(
            CraftingAttemptRecord(
                attempt_id=e.attempt_id,
                session_id=str(e.session_id) if e.session_id else None,
                reagents=list(e.reagents),
                catalyst=e.catalyst,
                risk_score=e.risk_score,
                applies_to_character=e.applies_to_character,
            )
        )
        st.record("attempted", reagents=e.reagents, catalyst=e.catalyst, risk_score=e.risk_score)

    @handles(CraftingSucceeded)
    def handle_succeeded(self, e: CraftingSucceeded) -> None:
        self.state.successful_crafts += 1
        if e.recipe_name not in self.state.discovered_recipes:
            self.state.discovered_recipes.append(e.recipe_name)
        attempt = self._open_attempt()
        attempt.outcome_event_id = str(e.event_id)
        attempt.outcome = "success"
        attempt.item_name = e.item_name
        attempt.recipe_name = e.recipe_name
        attempt.quantity = e.quantity
        attempt.tags = list(e.tags)
        self.state.record("succeeded", item_name=e.item_name, quantity=e.quantity, tags=e.tags)

    @handles(CraftingMishapOccurred)
    def handle_mishap(self, e: CraftingMishapOccurred) -> None:
        self.state.mishaps_count += 1
        attempt = self._open_attempt()
        attempt.outcome_event_id = str(e.event_id)
        attempt.outcome = "mishap"
        attempt.mishap = {
            "mishap_type": e.mishap_type,
            "severity": e.severity,
            "description": e.description,
            "damage": e.damage_dealt,
            "condition": e.condition_inflicted,
        }
        self.state.record(
            "mishap",
            mishap_type=e.mishap_type,
            severity=e.severity,
            damage_dealt=e.damage_dealt,
            condition=e.condition_inflicted,
        )

    def _open_attempt(self) -> CraftingAttemptRecord:
        """Return the newest attempt that has no outcome yet. Its outcome event follows it."""
        for attempt in reversed(self.state.attempts):
            if attempt.outcome_event_id is None:
                return attempt
        raise RuntimeError("A crafting outcome arrived without a recorded attempt")

    def find_attempt(self, attempt_id: UUID) -> CraftingAttemptRecord | None:
        """Return the recorded attempt with this client attempt id, or None."""
        return next((a for a in self.state.attempts if a.attempt_id == attempt_id), None)

    def combine_reagents(
        self,
        character_id: UUID,
        reagents: list[str],
        catalyst: str | None = None,
        campaign_id: UUID | str = "",
        session_id: UUID | str = "",
        player_id: str | None = None,
        force_mishap: bool = False,
        risk_threshold: float = 0.50,
        attempt_id: UUID | None = None,
    ) -> CombineOutcome:
        """Combine reagents in crucible, evaluate volatile outcome, and record domain events."""
        camp, sess = (
            opaque_optional_aggregate_id(campaign_id, field="campaign_id"),
            opaque_optional_aggregate_id(session_id, field="session_id"),
        )
        att, ev_cls, kw, outcome = CraftingEngine.resolve(
            character_id, reagents, catalyst, camp, sess, player_id, force_mishap, risk_threshold
        )
        self.create_event(
            CraftingAttempted, **att, attempt_id=attempt_id, applies_to_character=True
        )
        self.create_event(ev_cls, **kw)
        return outcome


__all__ = ["CombineOutcome", "CraftingAggregate", "CraftingEngine", "CraftingState"]
