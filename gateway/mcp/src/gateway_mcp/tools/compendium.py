"""Rules compendium and encounter builder tools for FastMCP gateway.

Monster and balance facts live in the rules_compendium service. These tools call its
public routes and return what it serves.
"""

from typing import TYPE_CHECKING, Any

from gateway_mcp.clients import ServiceClient
from gateway_mcp.clients.caller import caller_bearer
from mcp.server.fastmcp import Context

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


async def query_monster_stat_block(monster_name: str, ctx: Context | None = None) -> dict[str, Any]:
    """Retrieve full canonical monster stat block by name (e.g. 'Goblin', 'Ogre', 'Young Red Dragon')."""
    monster = await ServiceClient(bearer=caller_bearer(ctx)).get_monster(monster_name.strip())
    return {"status": "success", "monster": monster}


async def calculate_encounter_balance(
    party_levels: list[int],
    target_difficulty: str = "Medium",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Calculate balanced combat encounter group and CR XP thresholds for a party roster."""
    return await ServiceClient(bearer=caller_bearer(ctx)).balance_encounter(
        party_levels, target_difficulty
    )


def register_compendium_tools(mcp: "FastMCP") -> None:
    """Register rules compendium and encounter builder tools on the FastMCP application."""
    mcp.tool()(query_monster_stat_block)
    mcp.tool()(calculate_encounter_balance)
