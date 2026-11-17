"""Rules compendium and encounter builder tools for FastMCP gateway."""

from typing import TYPE_CHECKING, Any

from gateway_mcp.clients import ServiceClient
from rules_compendium.srd import CANONICAL_MONSTERS

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def query_monster_stat_block(monster_name: str) -> dict[str, Any]:
    """Retrieve full canonical monster stat block by name (e.g. 'Goblin', 'Ogre', 'Young Red Dragon')."""
    for m in CANONICAL_MONSTERS:
        if m["name"].lower() == monster_name.lower().strip():
            return {"status": "success", "monster": m}

    return {
        "status": "not_found",
        "error": f"Monster '{monster_name}' not found in canonical compendium.",
    }


async def calculate_encounter_balance(
    party_levels: list[int],
    target_difficulty: str = "Medium",
) -> dict[str, Any]:
    """Calculate balanced combat encounter group and CR XP thresholds for a party roster."""
    return await ServiceClient().balance_encounter(party_levels, target_difficulty)


def register_compendium_tools(mcp: "FastMCP") -> None:
    """Register rules compendium and encounter builder tools on the FastMCP application."""
    mcp.tool()(query_monster_stat_block)
    mcp.tool()(calculate_encounter_balance)
