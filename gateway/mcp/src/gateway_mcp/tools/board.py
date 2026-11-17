"""Tactical board and encounter tools for FastMCP gateway.

Board facts live in the board_state service. These tools call its public
routes and return what it stores. They hold no board data of their own.
"""

from typing import TYPE_CHECKING, Any

from gateway_mcp.clients import ServiceClient
from pydantic import BaseModel

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

ENCOUNTER_COLS = 10
ENCOUNTER_ROWS = 8


class EnemyPlacement(BaseModel):
    """An enemy token to place when an encounter starts."""

    name: str
    x: int
    y: int
    hp: int | None = None


def _board_summary(board: dict[str, Any]) -> dict[str, Any]:
    """Shape a board_state board into the grid and token view used by agents."""
    return {
        "session_id": board["session_id"],
        "grid_dimensions": {"cols": board["cols"], "rows": board["rows"]},
        "tokens": list(board["tokens"].values()),
        "active_hazards": board["active_hazards"],
    }


async def inspect_tactical_board(session_id: str) -> dict[str, Any]:
    """Retrieve all tokens, coordinates, and grid dimensions for the active session."""
    board = await ServiceClient().get_board(session_id)
    return _board_summary(board)


async def move_board_token(session_id: str, token_id: str, to_x: int, to_y: int) -> dict[str, Any]:
    """Move a token to target coordinates (x, y) on the tactical map."""
    result = await ServiceClient().move_token(
        session_id,
        token_id,
        to_x=to_x,
        to_y=to_y,
        initiated_by="the_watcher",
    )
    return {
        "status": "success",
        "session_id": session_id,
        "token_id": result["token_id"],
        "destination": {"x": result["x"], "y": result["y"]},
        "movement_cost": result["movement_cost"],
        "trap_triggered": result["trap_triggered"],
        "movement_paused": result["movement_paused"],
    }


async def query_encounter_state(encounter_id: str) -> dict[str, Any]:
    """Query the board state of an encounter: tokens, grid, and active hazards.

    Turn order and round number are not tracked by the board service.
    """
    board = await ServiceClient().get_board(encounter_id)
    return _board_summary(board)


async def create_encounter(
    encounter_name: str,
    terrain: str = "dungeon",
    enemies: list[EnemyPlacement] | None = None,
) -> dict[str, Any]:
    """Create a tactical combat board and place the enemy tokens on it."""
    client = ServiceClient()
    board = await client.create_board(cols=ENCOUNTER_COLS, rows=ENCOUNTER_ROWS)
    encounter_id = board["session_id"]
    spawned: list[dict[str, Any]] = []
    for enemy in enemies or []:
        token = await client.place_token(
            encounter_id,
            name=enemy.name,
            token_type="monster",
            x=enemy.x,
            y=enemy.y,
            hp=enemy.hp,
            is_friendly=False,
        )
        spawned.append(token)
    return {
        "status": "encounter_created",
        "encounter_id": encounter_id,
        "name": encounter_name,
        "terrain": terrain,
        "grid": {"cols": board["cols"], "rows": board["rows"]},
        "enemies_spawned": spawned,
    }


def register_board_tools(mcp: "FastMCP") -> None:
    """Register board and encounter tools on the FastMCP application."""
    mcp.tool()(inspect_tactical_board)
    mcp.tool()(move_board_token)
    mcp.tool()(query_encounter_state)
    mcp.tool()(create_encounter)


__all__ = [
    "create_encounter",
    "inspect_tactical_board",
    "move_board_token",
    "query_encounter_state",
    "register_board_tools",
]
