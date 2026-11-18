"""Session and encounter FastMCP resources.

Each resource takes the session id from its URI and reads the owning service.
A session that the service does not know gives a resource error.
"""

from typing import TYPE_CHECKING, Any

from gateway_mcp.clients import ServiceClient
from gateway_mcp.clients.caller import caller_bearer
from gateway_mcp.tools.board import query_encounter_state
from mcp.server.fastmcp import Context

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


async def get_session_state(session_id: str, ctx: Context | None = None) -> dict[str, Any]:
    """Read the stored state of a game session from game_session."""
    session = await ServiceClient(bearer=caller_bearer(ctx)).get_session(session_id)
    return {
        "session_id": session["session_id"],
        "campaign_id": session["campaign_id"],
        "title": session["title"],
        "dm_id": session["dm_id"],
        "status": session["status"],
        "current_turn": session["current_turn"],
        "in_combat": session["in_combat"],
        "combat_round": session["combat_round"],
        "combat_active_id": session["combat_active_id"],
        "participants": session["participants"],
    }


async def get_encounter_state(session_id: str, ctx: Context | None = None) -> dict[str, Any]:
    """Read the encounter of a session: tokens and grid from board_state, round and order from game_session."""
    return await query_encounter_state(session_id, ctx=ctx)


def register_session_resources(mcp: "FastMCP") -> None:
    """Register session and encounter resources on FastMCP."""
    mcp.resource("session://{session_id}/state", mime_type="application/json")(get_session_state)
    mcp.resource("encounter://{session_id}/current", mime_type="application/json")(
        get_encounter_state
    )
