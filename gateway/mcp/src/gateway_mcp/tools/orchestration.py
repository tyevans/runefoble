"""Agent action planning and Watcher DM orchestration tools."""

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_mcp_instance: Any = None


def narrate_with_the_watcher(scene_prompt: str, player_actions: str) -> dict[str, Any]:
    """Invoke The Watcher AI Game Master to arbitrate actions and generate immersive narration."""
    return {
        "scene_prompt": scene_prompt,
        "player_actions": player_actions,
        "narration": (
            f"The Watcher weaves fate: As {player_actions}, the stone beneath your boots trembles. "
            "Ancient glyphs ignite along the chamber ceiling."
        ),
        "environmental_effects": ["flickering_shadows", "low_rumble"],
    }


async def execute_agent_action_plan(
    session_id: str, actions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Sequentially validate and execute a multi-turn agent action plan, collecting step results and timings."""
    step_results: list[dict[str, Any]] = []
    total_duration_ms: float = 0.0

    def _fail(
        err: str, idx: int, tool_name: str, duration: float = 0.0, output: Any = None
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "step": idx + 1,
            "tool": tool_name,
            "status": "error",
            "error": err,
            "duration_ms": duration,
        }
        if output is not None:
            entry["output"] = output
        step_results.append(entry)
        return {
            "status": "error",
            "success": False,
            "session_id": session_id,
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

        raw = action.get("parameters") or action.get("arguments") or action.get("args")
        params = (
            dict(raw)
            if isinstance(raw, dict)
            else {
                k: v
                for k, v in action.items()
                if k not in {"tool", "name", "tool_name", "step_id", "description"}
            }
        )

        if "session_id" not in params and tool_name in {
            "move_board_token",
            "inspect_tactical_board",
        }:
            params["session_id"] = session_id

        if tool_name == "move_board_token":
            to_x, to_y = params.get("to_x"), params.get("to_y")
            if to_x is not None and to_y is not None and not (0 <= to_x < 8 and 0 <= to_y < 8):
                return _fail(
                    f"Coordinates ({to_x}, {to_y}) out of grid bounds (8x8)",
                    idx,
                    tool_name,
                )

        t0 = time.perf_counter()
        try:
            output = await tool.run(params)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            total_duration_ms += duration_ms

            if isinstance(output, dict) and output.get("status") == "error":
                return _fail(
                    output.get("error", "Step returned error status"),
                    idx,
                    tool_name,
                    duration_ms,
                    output,
                )

            step_results.append(
                {
                    "step": idx + 1,
                    "tool": tool_name,
                    "status": "success",
                    "output": output,
                    "duration_ms": duration_ms,
                }
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return _fail(str(exc), idx, tool_name, duration_ms)

    return {
        "status": "success",
        "success": True,
        "session_id": session_id,
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
