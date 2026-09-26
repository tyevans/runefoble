"""Model Context Protocol (MCP) Gateway Server.

Exposes Runefoble tactical tools, board state, spells, conditions,
and AI DM controls to MCP-compliant agents and LLMs.
"""

from gateway_mcp.prompts import (
    dm_narrative_guidance,
    register_prompts,
    tactical_action_adviser,
)
from gateway_mcp.resources import (
    get_active_session_context,
    get_combat_encounter_state,
    get_session_state,
    register_resources,
)
from gateway_mcp.tools import (
    add_condition,
    apply_absentee_penalty,
    apply_condition,
    cast_spell,
    create_encounter,
    execute_agent_action_plan,
    get_character_sheet,
    inspect_inventory,
    inspect_tactical_board,
    modify_character_hp,
    move_board_token,
    narrate_with_the_watcher,
    query_encounter_state,
    register_tools,
    roll_dice,
)
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Runefoble MCP Gateway")
mcp.get_tool = mcp._tool_manager.get_tool

# Mount tool, resource, and prompt registration hooks
register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)

__all__ = [
    "add_condition",
    "apply_absentee_penalty",
    "apply_condition",
    "cast_spell",
    "create_encounter",
    "dm_narrative_guidance",
    "execute_agent_action_plan",
    "get_active_session_context",
    "get_character_sheet",
    "get_combat_encounter_state",
    "get_session_state",
    "inspect_inventory",
    "inspect_tactical_board",
    "main",
    "mcp",
    "modify_character_hp",
    "move_board_token",
    "narrate_with_the_watcher",
    "query_encounter_state",
    "roll_dice",
    "tactical_action_adviser",
]


def main() -> None:
    """Run FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
