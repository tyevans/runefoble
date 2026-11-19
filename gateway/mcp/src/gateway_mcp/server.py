"""Model Context Protocol (MCP) Gateway Server.

Exposes Runefoble tactical tools, board state, spells, conditions,
and AI DM controls to MCP-compliant agents and LLMs.

`build_mcp` builds one FastMCP app from one `GatewayMcpContainer` (TASK-0746). The module
keeps no app instance of its own, so two apps never share a registry.
"""

import uvicorn
from mcp.server.fastmcp import FastMCP
from runefoble_auth.principal import require_principal
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_publish import event_publish_failures
from runefoble_platform.telemetry import init_telemetry
from starlette.requests import Request
from starlette.responses import JSONResponse

from gateway_mcp.container import GatewayMcpContainer
from gateway_mcp.identity import BearerTransportAuth, get_verifier
from gateway_mcp.prompts.narrative import register_narrative_prompts
from gateway_mcp.resources.session import register_session_resources
from gateway_mcp.routers.tools_registry import mount_tools_registry
from gateway_mcp.settings import load_listen_settings, load_settings
from gateway_mcp.tools.board import register_board_tools
from gateway_mcp.tools.character import register_character_tools
from gateway_mcp.tools.compendium import register_compendium_tools
from gateway_mcp.tools.dice import register_dice_tools
from gateway_mcp.tools.orchestration import register_orchestration_tools


def build_mcp(container: GatewayMcpContainer) -> FastMCP:
    """Return a FastMCP app whose tools, resources, and registry all use `container`."""
    mcp = FastMCP("Runefoble MCP Gateway")
    container.registry.set_mcp_server(mcp)
    register_dice_tools(mcp)
    register_board_tools(mcp, container)
    register_character_tools(mcp, container)
    register_orchestration_tools(mcp, container)
    register_compendium_tools(mcp, container)
    register_session_resources(mcp, container)
    register_narrative_prompts(mcp)

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

    return mcp


def build_http_app(container: GatewayMcpContainer) -> BearerTransportAuth:
    """Return the MCP app with the tool admin routes. Every request needs a verified bearer (ADR-0015 c)."""
    app = build_mcp(container).streamable_http_app()
    mount_tools_registry(app, require_principal(get_verifier), container)
    return BearerTransportAuth(app)


def main() -> None:
    """Serve the MCP protocol over streamable HTTP on GATEWAY_MCP_HOST and GATEWAY_MCP_PORT.

    Requests without a verified bearer token are refused before any tool runs.

    The upstream URLs are read first, so a missing URL stops the process before it listens.
    """
    load_settings()
    platform_settings = PlatformSettings()
    init_telemetry("gateway-mcp", settings=platform_settings)
    listen = load_listen_settings()
    uvicorn.run(
        build_http_app(GatewayMcpContainer.default()),
        host=listen.host,
        port=listen.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
