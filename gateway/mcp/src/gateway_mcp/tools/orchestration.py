"""Agent action planning and Watcher DM orchestration tools.

The Watcher owns narration and action decisions. These tools forward agent requests to
the_watcher public routes and return its answer unchanged.
"""

from typing import TYPE_CHECKING, Any, Literal

from mcp.server.fastmcp import Context

from gateway_mcp.caller import caller_bearer
from gateway_mcp.container import GatewayMcpContainer, bind_container
from gateway_mcp.owning_services import OwningServices
from gateway_mcp.tool_authz import (
    ToolAuthzError,
    check_requirement,
    require_caller_id,
    step_requirement,
)
from gateway_mcp.tools.plan import Authorize, PlanPorts, PlanStepError, run_plan

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

Tone = Literal["dark_fantasy", "epic_heroic", "tense_mystery", "whimsical", "gritty"]


async def narrate_with_the_watcher(
    container: GatewayMcpContainer,
    campaign_id: str,
    session_id: str,
    scene_prompt: str,
    player_actions: str,
    scene_environment: str,
    tone: Tone = "dark_fantasy",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Ask The Watcher AI Game Master to narrate the scene after the player actions."""
    request = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "prompt": f"{scene_prompt}\nPlayer actions: {player_actions}",
        "scene_environment": scene_environment,
        "tone": tone,
    }
    return await OwningServices(container.service_clients, bearer=caller_bearer(ctx)).narrate(
        request
    )


async def execute_agent_action_plan(
    container: GatewayMcpContainer,
    session_id: str,
    campaign_id: str,
    actions: list[dict[str, Any]],
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Propose each step of an agent action plan to The Watcher, in order.

    Each step becomes a pending action. The DM can veto or change it before it takes
    effect. Planning stops at the first step that fails, and later steps do not run.
    """
    caller_id = require_caller_id(ctx)
    client = OwningServices(container.service_clients, bearer=caller_bearer(ctx))
    ports = PlanPorts(
        tool_exists=container.registry.has_tool,
        authorize=_step_authorizer(container, caller_id, session_id),
        propose=client.propose_action,
    )
    return await run_plan(actions, session_id=session_id, campaign_id=campaign_id, ports=ports)


def _step_authorizer(container: GatewayMcpContainer, caller_id: str, session_id: str) -> Authorize:
    """Return the port that checks one step's schema permission for the verified caller."""

    async def authorize(tool: str, params: dict[str, Any]) -> None:
        try:
            requirement = step_requirement(
                container.registry, tool, {"session_id": session_id, **params}
            )
            if requirement is not None:
                await check_requirement(container.permissions, caller_id, requirement)
        except ToolAuthzError as exc:
            raise PlanStepError(str(exc), tool) from exc

    return authorize


def register_orchestration_tools(mcp: "FastMCP", container: GatewayMcpContainer) -> None:
    """Register orchestration and Watcher DM tools on the FastMCP application."""
    mcp.tool()(bind_container(narrate_with_the_watcher, container))
    mcp.tool()(bind_container(execute_agent_action_plan, container))
