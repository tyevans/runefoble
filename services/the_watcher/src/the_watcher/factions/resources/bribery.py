"""Bribery and influence adjudication logic for NPC factions."""

from __future__ import annotations

import random
from typing import Any

LOYALTY_DC_MODIFIERS: dict[str, int] = {
    "incorruptible": 15,
    "fanatical": 10,
    "loyal": 5,
    "neutral": 0,
    "corruptible": -3,
    "greedy": -5,
}

ROLE_DC_MODIFIERS: dict[str, int] = {
    "guard_captain": 3,
    "high_official": 4,
    "judge": 4,
    "official": 2,
    "guard": 0,
    "clerk": 0,
    "merchant": 1,
    "dockworker": -2,
    "informant": -3,
}


def calculate_bribery_outcome(
    target_name: str,
    target_role: str = "official",
    bribe_amount: int = 0,
    target_loyalty: str = "neutral",
    counter_bribe: int = 0,
    roll: int | None = None,
) -> dict[str, Any]:
    """Calculate bribery DC, d20 test result, and narrative outcome."""
    base_dc = 15
    loyalty_mod = LOYALTY_DC_MODIFIERS.get(target_loyalty.lower(), 0)
    role_mod = ROLE_DC_MODIFIERS.get(target_role.lower(), 0)
    counter_mod = max(0, counter_bribe // 50)

    dc = max(5, base_dc + loyalty_mod + role_mod + counter_mod)
    modifier = min(10, max(0, bribe_amount // 50))

    actual_roll = roll if roll is not None else random.randint(1, 20)
    total_roll = actual_roll + modifier

    if actual_roll == 1:
        success = False
        outcome = "critical_failure"
        narrative = f"{target_name} ({target_role}) was deeply insulted by the bribe attempt and raised an alarm!"
    elif actual_roll == 20:
        success = True
        outcome = "critical_success"
        narrative = f"{target_name} ({target_role}) eagerly accepted {bribe_amount} gold and pledged full cooperation."
    elif total_roll >= dc:
        success = True
        outcome = "success"
        narrative = f"{target_name} ({target_role}) accepted {bribe_amount} gold (Roll: {actual_roll}+{modifier} vs DC {dc})."
    else:
        success = False
        if counter_bribe > 0:
            outcome = "countered"
            narrative = f"{target_name} ({target_role}) rejected the bribe, sway held by a rival's {counter_bribe} gold counter-bribe."
        else:
            outcome = "failure"
            narrative = f"{target_name} ({target_role}) declined the {bribe_amount} gold bribe (Roll: {actual_roll}+{modifier} vs DC {dc})."

    return {
        "dc": dc,
        "roll": actual_roll,
        "modifier": modifier,
        "total_roll": total_roll,
        "success": success,
        "outcome": outcome,
        "narrative": narrative,
    }
