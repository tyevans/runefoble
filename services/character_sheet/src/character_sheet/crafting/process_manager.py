"""Crafting process manager: applies recorded combine outcomes to the character (TASK-0772).

A combine has two aggregates. The crafting aggregate is the commit point: it records the
attempt, its outcome, the damage, and the reagents spent. The character then applies that
outcome and records a `CharacterCraftingOutcomeApplied` event keyed by the crafting outcome
event id. The character saves the applied marker in the same save as the applied effects, so
one stream never holds half of an apply.

A pending outcome is one that the crafting stream holds and the character has not applied.
Every combine and every character read applies pending outcomes first. A second apply of the
same outcome is a no-op.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

from character_sheet.aggregate import CharacterAggregate
from character_sheet.crafting.engine import CraftingAggregate
from character_sheet.crafting.recipes import CraftingAttemptRecord, CraftingState
from character_sheet.health_events import health_change_events
from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_platform.aggregate_loading import load_if_exists

Publisher = Callable[[Any], Awaitable[None]]


def pending_attempts(
    char: CharacterAggregate, crafting_state: CraftingState
) -> list[CraftingAttemptRecord]:
    """Return the recorded outcomes that this character has not applied yet, oldest first.

    Attempts recorded before the process manager have `applies_to_character` False and are
    never pending.
    """
    applied = set(char.state.applied_crafting_event_ids)
    return [
        attempt
        for attempt in crafting_state.attempts
        if attempt.applies_to_character
        and attempt.outcome_event_id is not None
        and attempt.outcome_event_id not in applied
    ]


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


def _apply_attempt(char: CharacterAggregate, attempt: CraftingAttemptRecord) -> list[Any]:
    """Apply one recorded outcome to the character. Return the health events to publish."""
    _consume_reagents(char, attempt.reagents)
    health_events: list[Any] = []
    if attempt.outcome == "success":
        char.add_inventory_item(
            item_id=str(uuid4()),
            name=attempt.item_name,
            quantity=attempt.quantity,
            weight_lbs=0.5,
        )
    elif attempt.mishap is not None:
        damage = int(attempt.mishap.get("damage", 0))
        if damage > 0:
            was_stabilized = char.state.is_stabilized
            char.modify_health(
                delta=-damage,
                source="crafting_mishap",
                session_id=attempt.session_id,
            )
            health_events = health_change_events(
                char.aggregate_id,
                char,
                delta=-damage,
                source="crafting_mishap",
                session_id=attempt.session_id,
                was_stabilized=was_stabilized,
            )
        if attempt.mishap.get("condition"):
            char.apply_condition(attempt.mishap["condition"], source="crafting_mishap")
    char.record_crafting_outcome_applied(
        attempt.outcome_event_id or "",
        str(attempt.attempt_id) if attempt.attempt_id else None,
    )
    return health_events


async def apply_pending_outcomes(
    char_repo: AggregateRepository[CharacterAggregate],
    char: CharacterAggregate,
    crafting_state: CraftingState,
    publish_character: Publisher,
) -> None:
    """Apply every pending outcome, save the character once, then publish the health events."""
    pending = pending_attempts(char, crafting_state)
    if not pending:
        return
    health_events: list[Any] = []
    for attempt in pending:
        health_events.extend(_apply_attempt(char, attempt))
    await char_repo.save(char)
    for health_event in health_events:
        await publish_character(health_event)


async def apply_pending_for_character(
    char_repo: AggregateRepository[CharacterAggregate],
    crafting_repo: AggregateRepository[CraftingAggregate],
    character_id: UUID,
    publish_character: Publisher,
) -> None:
    """Apply pending crafting outcomes for one character. A missing stream applies nothing."""
    char = await load_if_exists(char_repo, character_id)
    if char is None:
        return
    crafting = await load_if_exists(crafting_repo, character_id)
    if crafting is None:
        return
    await apply_pending_outcomes(char_repo, char, crafting.state, publish_character)


__all__ = ["apply_pending_for_character", "apply_pending_outcomes", "pending_attempts"]
