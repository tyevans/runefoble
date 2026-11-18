"""Standard events for one character health change. Every health route publishes them (TASK-0729)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from character_sheet.aggregate import CharacterAggregate
from runefoble_events.events import CharacterDamaged, CharacterHealthChanged, StandInStabilized


def health_change_events(
    character_id: UUID,
    char: CharacterAggregate,
    *,
    delta: int,
    source: str,
    session_id: str | None,
    was_stabilized: bool,
) -> list[Any]:
    """Return the events that one health change publishes, in publish order.

    The order is StandInStabilized (only when this change stabilizes the character),
    CharacterHealthChanged, and CharacterDamaged (only when delta is negative).
    Call this after the character is saved.
    """
    events: list[Any] = []
    if not was_stabilized and char.state.is_stabilized:
        events.append(
            StandInStabilized(
                aggregate_id=character_id,
                character_id=str(character_id),
                current_hp=0,
                condition="unconscious_stabilized",
            )
        )
    events.append(
        CharacterHealthChanged(
            aggregate_id=character_id,
            session_id=session_id or None,
            campaign_id=char.state.campaign_id or None,
            delta=delta,
            current_hp=char.state.current_hp,
            max_hp=char.state.max_hp,
            source=source,
        )
    )
    if delta < 0:
        events.append(
            CharacterDamaged(
                aggregate_id=character_id,
                character_id=str(character_id),
                delta=delta,
                current_hp=char.state.current_hp,
                max_hp=char.state.max_hp,
                source=source,
            )
        )
    return events


__all__ = ["health_change_events"]
