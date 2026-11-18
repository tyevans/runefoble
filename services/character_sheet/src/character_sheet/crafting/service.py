"""Reagent combination as one typed service call (TASK-0729, ADR-0015 f).

Order of work: load the character (not found is an error, a store failure propagates), load
the crafting history, consume reagents, craft, apply the outcome, save the character, save the
crafting history, then publish. Nothing is published before both saves succeed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID, uuid4

from character_sheet.aggregate import CharacterAggregate
from character_sheet.crafting.engine import CombineOutcome, CraftingAggregate
from character_sheet.health_events import health_change_events
from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create

Publisher = Callable[[Any], Awaitable[None]]


class CharacterNotFoundError(LookupError):
    """The character stream does not exist. Nothing is saved or published."""


@dataclass(frozen=True)
class CombineResult:
    outcome: Literal["success", "mishap"]
    risk_score: float
    character_current_hp: int
    character_conditions: list[str]
    item_name: str | None = None
    recipe_name: str | None = None
    quantity: int = 1
    tags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    reagents_consumed: list[str] = field(default_factory=list)
    catalyst_consumed: str | None = None
    mishap: dict[str, Any] | None = None


def _consume_reagents(char: CharacterAggregate, reagents: list[str]) -> None:
    """Remove one matching inventory item per reagent name. Unmatched names consume nothing."""
    for reagent_name in reagents:
        matching_item = next(
            (
                item
                for item in char.state.inventory.values()
                if item.name.lower() == reagent_name.lower()
            ),
            None,
        )
        if matching_item:
            char.remove_inventory_item(matching_item.item_id, quantity=1)


def _apply_outcome(
    char: CharacterAggregate, outcome: CombineOutcome, session_id: str | None
) -> list[Any]:
    """Change the character for the outcome. Return the health events to publish after save."""
    if outcome.outcome == "success":
        char.add_inventory_item(
            item_id=str(uuid4()),
            name=outcome.item_name,
            quantity=outcome.quantity,
            weight_lbs=0.5,
        )
        return []

    mishap = outcome.mishap
    if mishap is None:
        raise RuntimeError("A mishap outcome must carry its mishap record")
    damage = int(mishap.get("damage", 0))
    health_events: list[Any] = []
    if damage > 0:
        was_stabilized = char.state.is_stabilized
        char.modify_health(delta=-damage, source="crafting_mishap", session_id=session_id)
        health_events = health_change_events(
            char.aggregate_id,
            char,
            delta=-damage,
            source="crafting_mishap",
            session_id=session_id,
            was_stabilized=was_stabilized,
        )
    if mishap.get("condition"):
        char.apply_condition(mishap["condition"], source="crafting_mishap")
    return health_events


class CombineReagentsService:
    """Combine reagents for one character. Publishers are injected by the router."""

    def __init__(
        self,
        char_repo: AggregateRepository[CharacterAggregate],
        crafting_repo: AggregateRepository[CraftingAggregate],
        publish_character: Publisher,
        publish_crafting: Publisher,
    ) -> None:
        self._char_repo = char_repo
        self._crafting_repo = crafting_repo
        self._publish_character = publish_character
        self._publish_crafting = publish_crafting

    async def combine(
        self,
        *,
        character_id: UUID,
        reagents: list[str],
        catalyst: str | None,
        campaign_id: UUID | str,
        session_id: UUID | str,
        player_id: str | None,
        force_mishap: bool,
        risk_threshold: float,
    ) -> CombineResult:
        char = await load_if_exists(self._char_repo, character_id)
        if char is None:
            raise CharacterNotFoundError(str(character_id))
        crafting = await load_or_create(self._crafting_repo, character_id, CraftingAggregate)

        _consume_reagents(char, reagents)
        outcome = crafting.combine_reagents(
            character_id=character_id,
            reagents=reagents,
            catalyst=catalyst,
            campaign_id=campaign_id,
            session_id=session_id,
            player_id=player_id,
            force_mishap=force_mishap,
            risk_threshold=risk_threshold,
        )
        crafting_events = list(crafting.uncommitted_events)
        health_events = _apply_outcome(char, outcome, str(session_id) if session_id else None)

        await self._char_repo.save(char)
        await self._crafting_repo.save(crafting)

        for crafting_event in crafting_events:
            await self._publish_crafting(crafting_event)
        for health_event in health_events:
            await self._publish_character(health_event)

        return CombineResult(
            outcome=outcome.outcome,
            risk_score=outcome.risk_score,
            character_current_hp=char.state.current_hp,
            character_conditions=[
                c if isinstance(c, str) else getattr(c, "name", str(c))
                for c in char.state.conditions
            ],
            item_name=outcome.item_name,
            recipe_name=outcome.recipe_name,
            quantity=outcome.quantity,
            tags=outcome.tags,
            properties=outcome.properties,
            reagents_consumed=outcome.reagents_consumed,
            catalyst_consumed=outcome.catalyst_consumed,
            mishap=outcome.mishap,
        )


__all__ = ["CharacterNotFoundError", "CombineReagentsService", "CombineResult"]
