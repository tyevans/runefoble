"""Model Context Protocol (MCP) Gateway Server.

Exposes Runefoble tactical tools, board state, spells, conditions,
and AI DM controls to MCP-compliant agents and LLMs.
"""

from gateway_mcp.dynamic import dynamic_registry
from gateway_mcp.prompts import (
    dm_narrative_guidance,
    register_prompts,
    tactical_action_adviser,
)
from gateway_mcp.resources import (
    get_encounter_state,
    get_session_state,
    register_resources,
)
from gateway_mcp.settings import load_listen_settings, load_settings
from gateway_mcp.tools import (
    add_condition,
    apply_absentee_penalty,
    apply_condition,
    calculate_encounter_balance,
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
    query_monster_stat_block,
    register_tools,
    roll_dice,
)
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Runefoble MCP Gateway")

# Mount tool, resource, and prompt registration hooks
register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)

# Wire dynamic tool registry
dynamic_registry.set_mcp_server(mcp)

__all__ = [
    "add_condition",
    "apply_absentee_penalty",
    "apply_condition",
    "calculate_encounter_balance",
    "cast_spell",
    "create_encounter",
    "dm_narrative_guidance",
    "execute_agent_action_plan",
    "get_character_sheet",
    "get_encounter_state",
    "get_session_state",
    "inspect_inventory",
    "inspect_tactical_board",
    "main",
    "mcp",
    "modify_character_hp",
    "move_board_token",
    "narrate_with_the_watcher",
    "query_encounter_state",
    "query_monster_stat_block",
    "roll_dice",
    "tactical_action_adviser",
]


def main() -> None:
    """Serve the MCP protocol over streamable HTTP on GATEWAY_MCP_HOST and GATEWAY_MCP_PORT.

    The upstream URLs are read first, so a missing URL stops the process before it listens.
    """
    load_settings()
    listen = load_listen_settings()
    mcp.settings.host = listen.host
    mcp.settings.port = listen.port
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
