"""Rules compendium and encounter builder tools for FastMCP gateway."""

from typing import TYPE_CHECKING, Any

from rules_compendium.dependencies import get_retrieval_engine
from rules_compendium.encounter_builder import (
    build_balanced_encounter,
    calculate_party_thresholds,
)
from rules_compendium.srd_data import CANONICAL_MONSTERS

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def query_monster_stat_block(monster_name: str) -> dict[str, Any]:
    """Retrieve full canonical monster stat block by name (e.g. 'Goblin', 'Ogre', 'Young Red Dragon')."""
    engine = get_retrieval_engine()
    monster = engine.get_monster(monster_name)
    if monster:
        return {"status": "success", "monster": monster}

    # Fallback to direct SRD scan
    for m in CANONICAL_MONSTERS:
        if m["name"].lower() == monster_name.lower().strip():
            return {"status": "success", "monster": m}

    return {
        "status": "not_found",
        "error": f"Monster '{monster_name}' not found in canonical compendium.",
    }


def calculate_encounter_balance(
    party_levels: list[int],
    target_difficulty: str = "Medium",
) -> dict[str, Any]:
    """Calculate balanced combat encounter group and CR XP thresholds for a party roster."""
    if not party_levels:
        party_levels = [1]

    thresholds = calculate_party_thresholds(party_levels)
    monsters, total_raw_xp, multiplier, adjusted_xp, calculated_tier = build_balanced_encounter(
        party_levels=party_levels,
        target_difficulty=target_difficulty,
    )

    return {
        "status": "success",
        "party_levels": party_levels,
        "party_size": len(party_levels),
        "target_difficulty": target_difficulty,
        "calculated_tier": calculated_tier,
        "thresholds": thresholds,
        "raw_xp": total_raw_xp,
        "multiplier": multiplier,
        "adjusted_xp": adjusted_xp,
        "recommended_monsters": [m.model_dump() for m in monsters],
        "total_monster_count": sum(m.count for m in monsters),
    }


def register_compendium_tools(mcp: "FastMCP") -> None:
    """Register rules compendium and encounter builder tools on the FastMCP application."""
    mcp.tool()(query_monster_stat_block)
    mcp.tool()(calculate_encounter_balance)
