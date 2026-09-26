"""Dice rolling tools for FastMCP gateway."""

import random
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def roll_dice(notation: str = "1d20", reason: str = "Action check") -> dict[str, Any]:
    """Roll tabletop dice using standard RPG notation (e.g., '1d20', '2d6+3', '3d8-1')."""
    pattern = r"(\d+)d(\d+)(?:([+-])(\d+))?"
    match = re.match(pattern, notation.strip())
    if not match:
        rolls = [random.randint(1, 20)]
        return {
            "notation": "1d20",
            "rolls": rolls,
            "modifier": 0,
            "total": sum(rolls),
            "reason": reason,
        }

    count = int(match.group(1))
    sides = int(match.group(2))
    sign = match.group(3)
    mod = int(match.group(4)) if match.group(4) else 0
    modifier = -mod if sign == "-" else mod

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    return {
        "notation": notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "reason": reason,
    }


def register_dice_tools(mcp: "FastMCP") -> None:
    """Register dice rolling tools on the FastMCP application."""
    mcp.tool()(roll_dice)
