"""Character sheet, spellcasting, condition, and inventory tools.

Character facts live in the character_sheet service. These tools call its
public routes and return what it stores. They hold no character data of their
own and return no substitute values when the service fails.
"""

from typing import TYPE_CHECKING, Any

from gateway_mcp.clients import ServiceClient
from gateway_mcp.clients.caller import caller_bearer
from gateway_mcp.tool_authz import authorize_tool_call, character_edit, dm_action_on_character
from mcp.server.fastmcp import Context

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


async def inspect_inventory(character_id: str) -> dict[str, Any]:
    """Inspect a character's equipped items and carried inventory."""
    sheet = await ServiceClient().get_character(character_id)
    return {
        "character_id": sheet["character_id"],
        "equipped": sheet["equipment"],
        "inventory": list(sheet["inventory"].values()),
    }


async def get_character_sheet(character_id: str) -> dict[str, Any]:
    """Retrieve complete character sheet details including stats, hit points, equipment, and conditions."""
    sheet = await ServiceClient().get_character(character_id)
    return {
        "character_id": sheet["character_id"],
        "name": sheet["name"],
        "class": sheet["character_class"],
        "level": sheet["level"],
        "hp": {"current": sheet["current_hp"], "max": sheet["max_hp"]},
        "armor_class": sheet["armor_class"],
        "speed_ft": sheet["speed_ft"],
        "attributes": sheet["ability_scores"],
        "spell_slots": sheet["spell_slots"],
        "equipment": sheet["equipment"],
        "inventory": list(sheet["inventory"].values()),
        "conditions": list(sheet["conditions"].values()),
        "penalties": sheet["penalties"],
        "is_stabilized": sheet["is_stabilized"],
    }


async def apply_absentee_penalty(
    character_id: str, penalty_type: str, explanation: str, ctx: Context | None = None
) -> dict[str, Any]:
    """Impose a session miss penalty (e.g. 'drunk', 'foolishness', 'cowardice') on an absent player's PC."""
    await authorize_tool_call(ctx, dm_action_on_character(character_id))
    sheet = await ServiceClient(bearer=caller_bearer(ctx)).apply_penalty(
        character_id, penalty_type=penalty_type, description=explanation
    )
    return {
        "status": "applied",
        "character_id": sheet["character_id"],
        "penalty_type": penalty_type,
        "explanation": explanation,
        "active_penalties": sheet["penalties"],
    }


async def cast_spell(
    character_id: str,
    spell_name: str,
    spell_level: int = 1,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Cast a spell from a spell slot. Use spell_level 0 for a cantrip. The character sheet tracks slot expenditure."""
    await authorize_tool_call(ctx, character_edit(character_id))
    sheet = await ServiceClient(bearer=caller_bearer(ctx)).cast_spell(
        character_id, spell_name=spell_name, slot_level=spell_level
    )
    return {
        "status": "cast",
        "character_id": sheet["character_id"],
        "spell_name": spell_name,
        "spell_level": spell_level,
        "spell_slots": sheet["spell_slots"],
    }


async def modify_character_hp(
    character_id: str,
    delta: int,
    damage_type: str = "untyped",
    reason: str = "combat action",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Modify a character or token's hit points (negative for damage, positive for healing)."""
    await authorize_tool_call(ctx, dm_action_on_character(character_id))
    sheet = await ServiceClient(bearer=caller_bearer(ctx)).change_health(
        character_id, delta=delta, source=f"{reason} [{damage_type}]"
    )
    return {
        "status": "success",
        "character_id": sheet["character_id"],
        "hp_change": delta,
        "damage_type": damage_type,
        "reason": reason,
        "current_hp": sheet["current_hp"],
        "max_hp": sheet["max_hp"],
        "is_stabilized": sheet["is_stabilized"],
        "conditions": list(sheet["conditions"].keys()),
    }


async def add_condition(
    character_id: str,
    condition: str,
    duration_rounds: int | None = None,
    source: str = "unspecified",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Impose an active status condition or DM penalty on a character (e.g. 'blinded', 'prone', 'drunk', 'frightened')."""
    return await _impose_condition(character_id, condition, duration_rounds, source, ctx)


async def apply_condition(
    character_id: str,
    condition: str,
    duration_rounds: int | None = None,
    source: str = "unspecified",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Impose an active status condition or DM penalty on a character (e.g. 'blinded', 'prone', 'drunk', 'frightened')."""
    return await _impose_condition(character_id, condition, duration_rounds, source, ctx)


async def _impose_condition(
    character_id: str,
    condition: str,
    duration_rounds: int | None,
    source: str,
    ctx: Context | None,
) -> dict[str, Any]:
    """Send a condition to character_sheet and return the conditions it now stores."""
    await authorize_tool_call(ctx, dm_action_on_character(character_id))
    name = condition.lower().strip()
    sheet = await ServiceClient(bearer=caller_bearer(ctx)).apply_condition(
        character_id, condition=name, duration_rounds=duration_rounds, source=source
    )
    return {
        "status": "condition_applied",
        "character_id": sheet["character_id"],
        "condition": name,
        "duration_rounds": duration_rounds,
        "source": source,
        "active_conditions": list(sheet["conditions"].keys()),
    }


def register_character_tools(mcp: "FastMCP") -> None:
    """Register character and inventory tools on the FastMCP application."""
    mcp.tool()(get_character_sheet)
    mcp.tool()(inspect_inventory)
    mcp.tool()(apply_absentee_penalty)
    mcp.tool()(cast_spell)
    mcp.tool()(modify_character_hp)
    mcp.tool()(add_condition)
    mcp.tool()(apply_condition)
