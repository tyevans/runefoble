"""Reagent combination as one typed service call (TASK-0729, TASK-0772, ADR-0011).

Order of work for one combine:
1. Load the character. A missing stream is an error and nothing is saved.
2. Load the crafting history. A load failure propagates.
3. Apply pending outcomes of earlier combines (idempotent).
4. When the request carries an `attempt_id` that is already recorded, return the recorded
   outcome. Nothing is spent again.
5. Otherwise record the new attempt on the crafting aggregate and save it. This save is the
   commit point of the decision.
6. Apply the outcome to the character and save it. If this save fails, the request fails and
   the outcome stays pending. The next combine or character read applies it.

The crafting aggregate and the character are separate streams. Their saves are not atomic. The
process manager makes the character step idempotent, so a retry never applies an outcome twice.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from character_sheet.aggregate import CharacterAggregate
from character_sheet.crafting.engine import CraftingAggregate, CraftingEngine
from character_sheet.crafting.process_manager import apply_pending_outcomes
from character_sheet.crafting.recipes import CraftingAttemptRecord
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


def _result(attempt: CraftingAttemptRecord, char: CharacterAggregate) -> CombineResult:
    """Build the response from a recorded attempt and the character as it is now."""
    if attempt.outcome is None:
        raise RuntimeError("A combine result needs a recorded outcome")
    success = attempt.outcome == "success"
    return CombineResult(
        outcome=attempt.outcome,
        risk_score=attempt.risk_score,
        character_current_hp=char.state.current_hp,
        character_conditions=[
            c if isinstance(c, str) else getattr(c, "name", str(c)) for c in char.state.conditions
        ],
        item_name=attempt.item_name if success else None,
        recipe_name=attempt.recipe_name if success else None,
        quantity=attempt.quantity if success else 1,
        tags=attempt.tags if success else [],
        properties=CraftingEngine.evaluate_recipe(attempt.reagents)[3] if success else {},
        reagents_consumed=attempt.reagents if success else [],
        catalyst_consumed=attempt.catalyst if success else None,
        mishap=attempt.mishap,
    )


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
        attempt_id: UUID | None = None,
    ) -> CombineResult:
        char = await load_if_exists(self._char_repo, character_id)
        if char is None:
            raise CharacterNotFoundError(str(character_id))
        crafting = await load_or_create(self._crafting_repo, character_id, CraftingAggregate)

        await apply_pending_outcomes(self._char_repo, char, crafting.state, self._publish_character)

        if attempt_id is not None:
            recorded = crafting.find_attempt(attempt_id)
            if recorded is not None:
                return _result(recorded, char)

        crafting.combine_reagents(
            character_id=character_id,
            reagents=reagents,
            catalyst=catalyst,
            campaign_id=campaign_id,
            session_id=session_id,
            player_id=player_id,
            force_mishap=force_mishap,
            risk_threshold=risk_threshold,
            attempt_id=attempt_id,
        )
        crafting_events = list(crafting.uncommitted_events)
        await self._crafting_repo.save(crafting)
        for crafting_event in crafting_events:
            await self._publish_crafting(crafting_event)

        attempt = crafting.state.attempts[-1]
        await apply_pending_outcomes(self._char_repo, char, crafting.state, self._publish_character)
        return _result(attempt, char)


__all__ = ["CharacterNotFoundError", "CombineReagentsService", "CombineResult"]
