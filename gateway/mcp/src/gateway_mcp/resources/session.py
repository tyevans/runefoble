"""Session and encounter FastMCP resources."""

from typing import TYPE_CHECKING, Any

from gateway_mcp.tools.board import inspect_tactical_board, query_encounter_state

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

ACTIVE_SESSION_ID = "camp1"


async def get_session_state(session_id: str) -> dict[str, Any]:
    """Aggregate tactical board tokens and active scene atmosphere for a session."""
    board = await inspect_tactical_board(session_id)
    return {
        "session_id": session_id,
        "tokens": board["tokens"],
        "active_tokens": board["tokens"],
        "grid_dimensions": board["grid_dimensions"],
        "threat_level": "medium",
        "scene_atmosphere": {
            "mood": "ominous tension",
            "lighting": "dim flickering torches",
            "ambient_audio_prompt": "distant dripping water and echoing chanting",
            "threat_level": "medium",
        },
    }


async def get_active_session_context() -> dict[str, Any]:
    """Retrieve complete context for the currently active tabletop gaming session."""
    return await get_session_state(ACTIVE_SESSION_ID)


async def get_combat_encounter_state() -> dict[str, Any]:
    """Retrieve the board state of the active encounter (tokens, grid, and hazards)."""
    return await query_encounter_state(ACTIVE_SESSION_ID)


def register_session_resources(mcp: "FastMCP") -> None:
    """Register session and encounter resources on FastMCP."""
    mcp.resource("session://{session_id}/state", mime_type="application/json")(get_session_state)
    mcp.resource("session://active", mime_type="application/json")(get_active_session_context)
    mcp.resource("encounter://current", mime_type="application/json")(get_combat_encounter_state)
