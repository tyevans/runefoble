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
    r"\s*(\d+)?d(\d+)\s*(?:(kh|kl)\s*(\d+))?\s*(?:([+-])\s*(\d+))?\s*",
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
    _validate_dice_arguments(count, sides, keep_highest, keep_lowest)
    rolls = _roll_dice(count, sides, fixed_rolls)
    kept_rolls = _select_kept_rolls(rolls, keep_highest, keep_lowest)
    is_crit, is_fumble = _critical_flags(kept_rolls, sides)

    return {
        "count": count,
        "sides": sides,
        "modifier": modifier,
        "keep_highest": keep_highest,
        "keep_lowest": keep_lowest,
        "rolls": rolls,
        "kept_rolls": kept_rolls,
        "total": sum(kept_rolls) + modifier,
        "is_crit": is_crit,
        "is_fumble": is_fumble,
    }


def roll_die(sides: int, rng: random.Random | None = None) -> int:
    """Roll one die with `sides` faces. Use `rng` for a seeded, reproducible roll."""
    if sides < 1:
        raise ValueError(f"Dice sides must be at least 1, got {sides}")
    return (rng or random).randint(1, sides)


def roll_d20(explicit: int | None = None, rng: random.Random | None = None) -> int:
    """Return a d20 result. An explicit roll, such as a client-supplied value, wins."""
    if explicit is not None:
        return explicit
    return roll_die(20, rng)


def _validate_dice_arguments(
    count: int, sides: int, keep_highest: int | None, keep_lowest: int | None
) -> None:
    """Raise ValueError when the dice arguments cannot describe a roll."""
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


def _roll_dice(count: int, sides: int, fixed_rolls: list[int] | None) -> list[int]:
    """Return the roll results, or the preset results for deterministic tests."""
    if fixed_rolls is None:
        return [random.randint(1, sides) for _ in range(count)]
    if len(fixed_rolls) != count:
        raise ValueError(f"Expected {count} fixed rolls, got {len(fixed_rolls)}")
    return list(fixed_rolls)


def _select_kept_rolls(
    rolls: list[int], keep_highest: int | None, keep_lowest: int | None
) -> list[int]:
    """Return the rolls that count toward the total under the keep rule."""
    if keep_highest is not None:
        return sorted(rolls, reverse=True)[:keep_highest]
    if keep_lowest is not None:
        return sorted(rolls)[:keep_lowest]
    return list(rolls)


def _critical_flags(kept_rolls: list[int], sides: int) -> tuple[bool, bool]:
    """Return (is_crit, is_fumble). Both flags apply only to d20 rolls."""
    if sides != 20:
        return False, False
    if 20 in kept_rolls:
        return True, False
    return False, 1 in kept_rolls


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
    match = DICE_FORMULA_PATTERN.fullmatch(formula)
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
    "roll_d20",
    "roll_die",
    "DICE_FORMULA_PATTERN",
]
