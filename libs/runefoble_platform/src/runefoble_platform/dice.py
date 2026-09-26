"""Dice arithmetic engine and formula parser for Runefoble.

Provides evaluation of tabletop RPG dice expressions (e.g. 1d20+5, 2d20kh1+3, 8d6+4)
with support for advantage, disadvantage, stat generation drop-dice rules, and critical detection.
"""

from __future__ import annotations

import random
import re
from typing import Any

# Regex to capture expressions like:
# '1d20', '2d20kh1+3', '2d20kl1-2', '8d6+4', '4d6kh3', 'd20+5'
DICE_FORMULA_PATTERN = re.compile(
    r"^\s*(\d+)?d(\d+)\s*(?:(kh|kl)\s*(\d+))?\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)


def evaluate_dice(
    count: int,
    sides: int,
    modifier: int = 0,
    keep_highest: int | None = None,
    keep_lowest: int | None = None,
    *,
    fixed_rolls: list[int] | None = None,
) -> dict[str, Any]:
    """Evaluate a roll of `count` dice with `sides` faces and optional keep rules.

    Args:
        count: Number of dice to roll (>= 1).
        sides: Number of sides per die (>= 1).
        modifier: Additive integer modifier to total (can be positive, zero, or negative).
        keep_highest: If provided, keep only the top N highest rolls (e.g. advantage, 4d6kh3).
        keep_lowest: If provided, keep only the lowest N rolls (e.g. disadvantage).
        fixed_rolls: Optional preset list of roll results for deterministic testing.

    Returns:
        A dictionary containing roll results, kept rolls, total, and crit/fumble flags.
    """
    if count < 1:
        raise ValueError(f"Dice count must be at least 1, got {count}")
    if sides < 1:
        raise ValueError(f"Dice sides must be at least 1, got {sides}")
    if keep_highest is not None and keep_lowest is not None:
        raise ValueError("Cannot specify both keep_highest and keep_lowest")
    if keep_highest is not None and keep_highest < 0:
        raise ValueError(f"keep_highest cannot be negative, got {keep_highest}")
    if keep_lowest is not None and keep_lowest < 0:
        raise ValueError(f"keep_lowest cannot be negative, got {keep_lowest}")

    if fixed_rolls is not None:
        if len(fixed_rolls) != count:
            raise ValueError(f"Expected {count} fixed rolls, got {len(fixed_rolls)}")
        rolls = list(fixed_rolls)
    else:
        rolls = [random.randint(1, sides) for _ in range(count)]

    # Determine which rolls to keep
    if keep_highest is not None:
        sorted_rolls = sorted(rolls, reverse=True)
        kept_rolls = sorted_rolls[:keep_highest]
    elif keep_lowest is not None:
        sorted_rolls = sorted(rolls)
        kept_rolls = sorted_rolls[:keep_lowest]
    else:
        kept_rolls = list(rolls)

    total = sum(kept_rolls) + modifier

    # Critical hit and fumble flags apply specifically to d20 rolls
    is_crit = False
    is_fumble = False
    if sides == 20:
        if 20 in kept_rolls:
            is_crit = True
        elif 1 in kept_rolls:
            is_fumble = True

    return {
        "count": count,
        "sides": sides,
        "modifier": modifier,
        "keep_highest": keep_highest,
        "keep_lowest": keep_lowest,
        "rolls": rolls,
        "kept_rolls": kept_rolls,
        "total": total,
        "is_crit": is_crit,
        "is_fumble": is_fumble,
    }


def parse_and_roll(formula: str, *, fixed_rolls: list[int] | None = None) -> dict[str, Any]:
    """Parse standard TTRPG dice notation and evaluate the roll.

    Supported patterns:
        - `1d20+5`, `d20+5`
        - `2d20kh1+3` (advantage d20 keep highest 1)
        - `2d20kl1+3` (disadvantage d20 keep lowest 1)
        - `8d6+4` (e.g. Fireball)
        - `4d6kh3` (character stat generation)

    Args:
        formula: Formula string to parse and roll.
        fixed_rolls: Optional preset list of roll results for deterministic testing.

    Returns:
        Roll result dictionary with formula and evaluation metrics.
    """
    match = DICE_FORMULA_PATTERN.match(formula.strip())
    if not match:
        raise ValueError(f"Invalid dice formula: {formula!r}")

    count_str, sides_str, keep_mode, keep_val_str, sign, mod_val_str = match.groups()

    count = int(count_str) if count_str else 1
    sides = int(sides_str)

    keep_highest: int | None = None
    keep_lowest: int | None = None
    if keep_mode and keep_val_str:
        val = int(keep_val_str)
        if keep_mode.lower() == "kh":
            keep_highest = val
        elif keep_mode.lower() == "kl":
            keep_lowest = val

    modifier = 0
    if sign and mod_val_str:
        val = int(mod_val_str)
        modifier = -val if sign == "-" else val

    result = evaluate_dice(
        count=count,
        sides=sides,
        modifier=modifier,
        keep_highest=keep_highest,
        keep_lowest=keep_lowest,
        fixed_rolls=fixed_rolls,
    )
    result["formula"] = formula.strip()
    return result


__all__ = [
    "evaluate_dice",
    "parse_and_roll",
    "DICE_FORMULA_PATTERN",
]
