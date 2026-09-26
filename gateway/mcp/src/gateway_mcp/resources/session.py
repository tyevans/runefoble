"""Session and encounter FastMCP resources."""

from typing import TYPE_CHECKING, Any

from gateway_mcp.tools.board import inspect_tactical_board, query_encounter_state

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def get_session_state(session_id: str) -> dict[str, Any]:
    """Aggregate tactical board tokens, active scene atmosphere, and encounter state."""
    board = inspect_tactical_board(session_id)
    encounter = query_encounter_state(f"enc-{session_id}")
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
        "encounter_state": encounter,
    }


def get_active_session_context() -> dict[str, Any]:
    """Retrieve complete context for the currently active tabletop gaming session."""
    return get_session_state("camp1")


def get_combat_encounter_state() -> dict[str, Any]:
    """Retrieve active combat encounter state, initiative order, and hazards."""
    return query_encounter_state("enc-camp1")


def register_session_resources(mcp: "FastMCP") -> None:
    """Register session and encounter resources on FastMCP."""
    mcp.resource("session://{session_id}/state", mime_type="application/json")(get_session_state)
    mcp.resource("session://active", mime_type="application/json")(get_active_session_context)
    mcp.resource("encounter://current", mime_type="application/json")(get_combat_encounter_state)
