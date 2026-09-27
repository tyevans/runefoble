"""Alchemical crafting execution engine and event-sourced aggregate."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from character_sheet.crafting.mishaps import MishapResolver, calculate_volatile_risk
from character_sheet.crafting.recipes import CraftingState, find_matching_recipe
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.events import CraftingAttempted, CraftingMishapOccurred, CraftingSucceeded


def _to_uuid(v: UUID | str) -> UUID | None:
    try:
        return UUID(str(v)) if v else None
    except Exception:
        return None


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
    ) -> tuple[dict[str, Any], type, dict[str, Any], dict[str, Any]]:
        risk = calculate_volatile_risk(reagents, cat)
        att = {"character_id": cid, "player_id": pid, "campaign_id": camp}
        att.update(session_id=sess, reagents=reagents, catalyst=cat, risk_score=risk)
        if MishapResolver.is_mishap(risk, cat, force_mishap, thresh):
            mishap = MishapResolver.select_mishap(risk)
            m_kw = MishapResolver.event_kwargs(cid, mishap, reagents, camp, sess)
            res = {"outcome": "mishap", "mishap": mishap, "risk_score": risk}
            res["reagents_lost"] = reagents
            return att, CraftingMishapOccurred, m_kw, res

        item, rec, tags, props = cls.evaluate_recipe(reagents)
        res = {"outcome": "success", "item_name": item, "recipe_name": rec, "quantity": 1}
        res |= {"tags": tags, "properties": props, "risk_score": risk}
        res |= {"reagents_consumed": reagents, "catalyst_consumed": cat}

        s_kw = {k: v for k, v in res.items() if k not in ("outcome", "risk_score")}
        s_kw.update(character_id=cid, campaign_id=camp, session_id=sess)
        return att, CraftingSucceeded, s_kw, res


class CraftingAggregate(DeclarativeAggregate[CraftingState]):
    """Event-sourced aggregate managing alchemical experimentation and volatile risk."""

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
        st.record("attempted", reagents=e.reagents, catalyst=e.catalyst, risk_score=e.risk_score)

    @handles(CraftingSucceeded)
    def handle_succeeded(self, e: CraftingSucceeded) -> None:
        self.state.successful_crafts += 1
        if e.recipe_name not in self.state.discovered_recipes:
            self.state.discovered_recipes.append(e.recipe_name)
        self.state.record("succeeded", item_name=e.item_name, quantity=e.quantity, tags=e.tags)

    @handles(CraftingMishapOccurred)
    def handle_mishap(self, e: CraftingMishapOccurred) -> None:
        self.state.mishaps_count += 1
        self.state.record(
            "mishap",
            mishap_type=e.mishap_type,
            severity=e.severity,
            damage_dealt=e.damage_dealt,
            condition=e.condition_inflicted,
        )

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
    ) -> dict[str, Any]:
        """Combine reagents in crucible, evaluate volatile outcome, and record domain events."""
        camp, sess = _to_uuid(campaign_id), _to_uuid(session_id)
        att, ev_cls, kw, res = CraftingEngine.resolve(
            character_id, reagents, catalyst, camp, sess, player_id, force_mishap, risk_threshold
        )
        self.create_event(CraftingAttempted, **att)
        self.create_event(ev_cls, **kw)
        return res


__all__ = ["CraftingAggregate", "CraftingEngine", "CraftingState"]
