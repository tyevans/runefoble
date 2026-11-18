"""Dice rolling tools for FastMCP gateway.

The roll itself lives in `runefoble_platform.dice`. This tool adds the reason
and keeps the platform result shape.
"""

from typing import TYPE_CHECKING, Any

from runefoble_platform.dice import parse_and_roll

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def roll_dice(
    notation: str = "1d20",
    reason: str = "Action check",
    *,
    fixed_rolls: list[int] | None = None,
) -> dict[str, Any]:
    """Roll tabletop dice using standard RPG notation (e.g., '1d20', '2d6+3', '3d8-1').

    Bad notation is a tool error. No default roll is made.
    """
    result = parse_and_roll(notation, fixed_rolls=fixed_rolls)
    result["reason"] = reason
    return result


def register_dice_tools(mcp: "FastMCP") -> None:
    """Register dice rolling tools on the FastMCP application."""
    mcp.tool()(roll_dice)
