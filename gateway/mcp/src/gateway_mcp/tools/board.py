"""Tactical board and encounter tools for FastMCP gateway.

Board facts live in the board_state service. These tools call its public
routes and return what it stores. They hold no board data of their own.
"""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from gateway_mcp.caller import caller_bearer
from gateway_mcp.owning_services import OwningServices, ServiceRejectedError
from gateway_mcp.tool_authz import authorize_tool_call, session_control, token_move

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


def _combat_view(combat: dict[str, Any]) -> dict[str, Any]:
    """Shape a game_session combat state into the round and turn order view used by agents."""
    return {
        "in_combat": combat["in_combat"],
        "round": combat["combat_round"],
        "active_combatant_id": combat["combat_active_id"],
        "turn_order": combat["initiative_order"],
    }


async def _fetch_or_create_board(
    client: OwningServices, session_id: str, campaign_id: str | None
) -> dict[str, Any]:
    """Return the session board, creating it when board_state has none for the session.

    Only a 404 from board_state means "no board yet". Every other error propagates.
    """
    try:
        return await client.get_board(session_id)
    except ServiceRejectedError as exc:
        if exc.status_code != 404:
            raise
    return await client.create_board(
        session_id=session_id, campaign_id=campaign_id, cols=ENCOUNTER_COLS, rows=ENCOUNTER_ROWS
    )


async def inspect_tactical_board(session_id: str, ctx: Context | None = None) -> dict[str, Any]:
    """Retrieve all tokens, coordinates, and grid dimensions for the active session."""
    board = await OwningServices(bearer=caller_bearer(ctx)).get_board(session_id)
    return _board_summary(board)


async def move_board_token(
    session_id: str,
    token_id: str,
    to_x: int,
    to_y: int,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Move a token to target coordinates (x, y) on the tactical map."""
    await authorize_tool_call(ctx, token_move(token_id))
    result = await OwningServices(bearer=caller_bearer(ctx)).move_token(
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


async def query_encounter_state(encounter_id: str, ctx: Context | None = None) -> dict[str, Any]:
    """Query an encounter: round, turn order, active combatant, tokens, grid, and hazards.

    Round and turn order come from game_session. Tokens, grid, and hazards come from
    board_state. The encounter id is the game session id.
    """
    client = OwningServices(bearer=caller_bearer(ctx))
    board = await client.get_board(encounter_id)
    combat = await client.get_combat_state(encounter_id)
    return {**_board_summary(board), **_combat_view(combat)}


async def create_encounter(
    session_id: str,
    campaign_id: str | None = None,
    enemies: list[EnemyPlacement] | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start combat in a game session and place the enemy tokens on its board.

    A new board needs `campaign_id`. The caller must run that campaign.

    The session id is the encounter id. game_session starts combat first, so an
    unknown or unavailable session creates no board.
    """
    await authorize_tool_call(ctx, session_control(session_id))
    client = OwningServices(bearer=caller_bearer(ctx))
    enemy_list = enemies or []
    combat = await client.start_combat(
        session_id,
        combatants=[
            {"combatant_id": f"enemy-{index}", "name": enemy.name, "hp": enemy.hp, "is_npc": True}
            for index, enemy in enumerate(enemy_list, start=1)
        ],
    )
    board = await _fetch_or_create_board(client, session_id, campaign_id)
    spawned: list[dict[str, Any]] = []
    for enemy in enemy_list:
        token = await client.place_token(
            session_id,
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
        "encounter_id": session_id,
        "grid": {"cols": board["cols"], "rows": board["rows"]},
        "enemies_spawned": spawned,
        **_combat_view(combat),
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
