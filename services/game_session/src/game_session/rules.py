"""Combat round rules, initiative sorting, and turn rotation for game sessions."""

from typing import Any
from uuid import UUID

DEFAULT_COMBAT_ROUND: int = 1
DEFAULT_TURN_SECONDS: int = 60


def initiative_sort_key(combatant: dict[str, Any]) -> tuple[Any, int, str]:
    """Sorting key for combat initiative.

    Highest score first, PCs break ties over monsters/NPCs, then alphabetical name.
    """
    return (
        combatant.get("initiative_score", 0),
        1 if not combatant.get("is_npc", False) else 0,
        combatant.get("combatant_name", ""),
    )


def sort_initiative_order(combatants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return combatants sorted in descending initiative order according to D&D tie-breaker rules."""
    return sorted(combatants, key=initiative_sort_key, reverse=True)


def merge_initiative_roll(
    existing_order: list[dict[str, Any]],
    combatant_id: str,
    combatant_name: str,
    initiative_score: float | int,
    is_npc: bool = False,
) -> list[dict[str, Any]]:
    """Insert or update a combatant's initiative score and return the re-sorted order."""
    filtered = [c for c in existing_order if c.get("combatant_id") != combatant_id]
    new_entry = {
        "combatant_id": combatant_id,
        "combatant_name": combatant_name,
        "initiative_score": initiative_score,
        "is_npc": is_npc,
    }
    return sort_initiative_order(filtered + [new_entry])


def advance_initiative_turn(
    initiative_order: list[dict[str, Any]],
    current_active_id: str | None,
    current_round: int,
) -> tuple[str, int]:
    """Determine the next active combatant ID and current round number upon turn advancement."""
    if not initiative_order:
        raise ValueError("Cannot advance initiative: initiative order is empty")

    sorted_order = sort_initiative_order(initiative_order)
    ids = [c["combatant_id"] for c in sorted_order]

    if current_active_id in ids:
        curr_idx = ids.index(current_active_id)
        next_idx = (curr_idx + 1) % len(ids)
        next_round = current_round + 1 if next_idx == 0 else current_round
    else:
        next_idx = 0
        next_round = current_round

    return ids[next_idx], next_round


def resolve_initiative_rolled(
    current_order: list[dict[str, Any]],
    current_active_id: str | None,
    combat_turn_started: bool,
    combatant_id: str,
    combatant_name: str,
    initiative_score: float | int,
    is_npc: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    """Calculate the new sorted initiative order and updated active combatant ID."""
    order = merge_initiative_roll(
        current_order,
        combatant_id=combatant_id,
        combatant_name=combatant_name,
        initiative_score=initiative_score,
        is_npc=is_npc,
    )
    active_id = (
        current_active_id if combat_turn_started else (order[0]["combatant_id"] if order else None)
    )
    return order, active_id


def calculate_next_active_character(participants: dict[str, Any], current_turn: int) -> UUID | None:
    """Calculate the next character ID in turn order rotation."""
    if not participants:
        return None
    part_list = list(participants.values())
    next_idx = current_turn % len(part_list)
    return getattr(part_list[next_idx], "character_id", None)
