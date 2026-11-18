"""Model Context Protocol (MCP) Gateway Server.

Exposes Runefoble tactical tools, board state, spells, conditions,
and AI DM controls to MCP-compliant agents and LLMs.
"""

import uvicorn
from gateway_mcp.dynamic import dynamic_registry
from gateway_mcp.dynamic import set_event_bus as set_dynamic_event_bus
from gateway_mcp.identity import BearerTransportAuth
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
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import create_event_bus
from runefoble_platform.event_publish import event_publish_failures
from starlette.requests import Request
from starlette.responses import JSONResponse

mcp = FastMCP("Runefoble MCP Gateway")

# Mount tool, resource, and prompt registration hooks
register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)

# Wire dynamic tool registry
dynamic_registry.set_mcp_server(mcp)


def build_http_app() -> BearerTransportAuth:
    """Return the streamable HTTP MCP app. Every request needs a verified bearer (ADR-0015 c)."""
    return BearerTransportAuth(mcp.streamable_http_app())


def configure_dynamic_event_bus(settings: PlatformSettings) -> None:
    """Inject the Redis Streams bus that dynamic tool events publish to.

    Raises EventBusUnavailableError when no Redis URL is configured, so the gateway never
    runs dynamic tools with events that cannot reach the system stream.
    """
    set_dynamic_event_bus(create_event_bus(settings))


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request: Request) -> JSONResponse:
    """Report liveness and the count of publish failures seen by this process."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "gateway_mcp",
            "event_publish_failures": event_publish_failures(),
        }
    )


__all__ = [
    "add_condition",
    "apply_absentee_penalty",
    "apply_condition",
    "calculate_encounter_balance",
    "configure_dynamic_event_bus",
    "cast_spell",
    "create_encounter",
    "dm_narrative_guidance",
    "execute_agent_action_plan",
    "get_character_sheet",
    "get_encounter_state",
    "get_session_state",
    "inspect_inventory",
    "inspect_tactical_board",
    "build_http_app",
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

    Requests without a verified bearer token are refused before any tool runs.

    The upstream URLs are read first, so a missing URL stops the process before it listens.
    """
    load_settings()
    configure_dynamic_event_bus(PlatformSettings())
    listen = load_listen_settings()
    uvicorn.run(build_http_app(), host=listen.host, port=listen.port, log_level="info")


if __name__ == "__main__":
    main()
