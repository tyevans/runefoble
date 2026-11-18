"""Agent action planning and Watcher DM orchestration tools.

The Watcher owns narration and action decisions. These tools forward agent requests to
the_watcher public routes and return its answer unchanged.
"""

import time
from typing import TYPE_CHECKING, Any, Literal

from gateway_mcp.caller import caller_bearer
from gateway_mcp.owning_services import OwningServices, ServiceError
from mcp.server.fastmcp import Context

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_mcp_instance: Any = None

Tone = Literal["dark_fantasy", "epic_heroic", "tense_mystery", "whimsical", "gritty"]


async def narrate_with_the_watcher(
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
    return await OwningServices(bearer=caller_bearer(ctx)).narrate(request)


async def execute_agent_action_plan(
    session_id: str,
    campaign_id: str,
    actions: list[dict[str, Any]],
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Propose each step of an agent action plan to The Watcher, in order.

    Each step becomes a pending action. The DM can veto or change it before it takes
    effect. Planning stops at the first step that fails, and later steps do not run.
    """
    client = OwningServices(bearer=caller_bearer(ctx))
    step_results: list[dict[str, Any]] = []
    total_duration_ms: float = 0.0

    def _fail(err: str, idx: int, tool_name: str, duration: float = 0.0) -> dict[str, Any]:
        step_results.append(
            {
                "step": idx + 1,
                "tool": tool_name,
                "status": "error",
                "error": err,
                "duration_ms": duration,
            }
        )
        return {
            "status": "error",
            "success": False,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "error": err,
            "failed_step": idx + 1,
            "total_steps": len(actions),
            "completed_steps": idx,
            "steps": step_results,
            "total_duration_ms": round(total_duration_ms + duration, 2),
        }

    for idx, action in enumerate(actions):
        tool_name = action.get("tool") or action.get("name") or action.get("tool_name")
        if not tool_name:
            return _fail("Action missing 'tool' specification", idx, "unknown")

        tool = (
            _mcp_instance._tool_manager.get_tool(tool_name) if _mcp_instance is not None else None
        )
        if tool is None:
            return _fail(f"Invalid tool: '{tool_name}' not found", idx, tool_name)

        actor_name = action.get("actor_name")
        if not actor_name:
            return _fail("Action missing 'actor_name' specification", idx, tool_name)

        raw = action.get("parameters") or action.get("arguments") or action.get("args")
        params = (
            dict(raw)
            if isinstance(raw, dict)
            else {
                k: v
                for k, v in action.items()
                if k not in {"tool", "name", "tool_name", "actor_name", "step_id", "description"}
            }
        )
        target = params.get("target", params.get("token_id"))

        request = {
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": actor_name,
            "action_type": tool_name,
            "description": action.get("description") or tool_name,
            "target": str(target) if target is not None else None,
            "parameters": params,
        }

        t0 = time.perf_counter()
        try:
            pending = await client.propose_action(request)
        except ServiceError as exc:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return _fail(str(exc), idx, tool_name, duration_ms)

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        total_duration_ms += duration_ms
        step_results.append(
            {
                "step": idx + 1,
                "tool": tool_name,
                "status": "success",
                "output": pending,
                "duration_ms": duration_ms,
            }
        )

    return {
        "status": "success",
        "success": True,
        "session_id": session_id,
        "campaign_id": campaign_id,
        "total_steps": len(actions),
        "completed_steps": len(actions),
        "steps": step_results,
        "total_duration_ms": round(total_duration_ms, 2),
    }


def register_orchestration_tools(mcp: "FastMCP") -> None:
    """Register orchestration and Watcher DM tools on the FastMCP application."""
    global _mcp_instance
    _mcp_instance = mcp
    mcp.tool()(narrate_with_the_watcher)
    mcp.tool()(execute_agent_action_plan)
