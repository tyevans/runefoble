"""Tabletop RPG tools for FastMCP gateway."""

from typing import TYPE_CHECKING

from gateway_mcp.tools.board import (
    create_encounter,
    inspect_tactical_board,
    move_board_token,
    query_encounter_state,
    register_board_tools,
)
from gateway_mcp.tools.character import (
    add_condition,
    apply_absentee_penalty,
    apply_condition,
    cast_spell,
    get_character_sheet,
    inspect_inventory,
    modify_character_hp,
    register_character_tools,
)
from gateway_mcp.tools.dice import (
    register_dice_tools,
    roll_dice,
)
from gateway_mcp.tools.orchestration import (
    execute_agent_action_plan,
    narrate_with_the_watcher,
    register_orchestration_tools,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

__all__ = [
    "add_condition",
    "apply_absentee_penalty",
    "apply_condition",
    "cast_spell",
    "create_encounter",
    "execute_agent_action_plan",
    "get_character_sheet",
    "inspect_inventory",
    "inspect_tactical_board",
    "modify_character_hp",
    "move_board_token",
    "narrate_with_the_watcher",
    "query_encounter_state",
    "register_board_tools",
    "register_character_tools",
    "register_dice_tools",
    "register_orchestration_tools",
    "register_tools",
    "roll_dice",
]


def register_tools(mcp: "FastMCP") -> None:
    """Register all tabletop RPG tools onto the FastMCP server."""
    register_dice_tools(mcp)
    register_board_tools(mcp)
    register_character_tools(mcp)
    register_orchestration_tools(mcp)
