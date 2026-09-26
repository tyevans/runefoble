"""Character sheet, spellcasting, condition, and inventory tools."""

from typing import TYPE_CHECKING, Any

from gateway_mcp.constants import CONDITION_RULES, SPELL_EFFECTS

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def inspect_inventory(character_id: str) -> dict[str, Any]:
    """Inspect a character's equipped items, carried inventory, and currency."""
    return {
        "character_id": character_id,
        "equipped": {
            "main_hand": "Longsword +1",
            "off_hand": "Steel Shield",
            "armor": "Chain Mail (AC 16)",
        },
        "inventory": [
            {"item": "Healing Potion", "quantity": 2, "weight_lbs": 1.0},
            {"item": "Rations", "quantity": 5, "weight_lbs": 10.0},
            {"item": "Rope, Hempen (50 ft)", "quantity": 1, "weight_lbs": 10.0},
            {"item": "Tinderbox", "quantity": 1, "weight_lbs": 1.0},
        ],
        "currency": {"gold": 45, "silver": 18, "copper": 30},
        "total_weight_lbs": 48.0,
        "encumbered": False,
    }


def get_character_sheet(character_id: str) -> dict[str, Any]:
    """Retrieve complete character sheet details including stats, hit points, equipment, and conditions."""
    return {
        "character_id": character_id,
        "name": "Valeros" if character_id in {"char-1", "t1"} else "Kyra",
        "class": "Fighter" if character_id in {"char-1", "t1"} else "Cleric",
        "level": 3,
        "hp": {"current": 38, "max": 45, "temp": 0},
        "armor_class": 18,
        "attributes": {
            "strength": 16,
            "dexterity": 12,
            "constitution": 14,
            "intelligence": 10,
            "wisdom": 13,
            "charisma": 8,
        },
        "inventory": inspect_inventory(character_id),
        "conditions": ["drunk"] if character_id in {"char-2", "t2"} else [],
    }


def apply_absentee_penalty(
    character_id: str, penalty_type: str, explanation: str
) -> dict[str, Any]:
    """Impose a session miss penalty (e.g. 'drunk', 'foolishness', 'cowardice') on an absent player's PC."""
    return {
        "status": "applied",
        "character_id": character_id,
        "penalty_type": penalty_type,
        "explanation": explanation,
        "watcher_rule": f"AI stand-in will now express traits of '{penalty_type}' in dialogue and combat rolls.",
    }


def cast_spell(
    character_id: str,
    spell_name: str,
    spell_level: int = 1,
    target: str | None = None,
) -> dict[str, Any]:
    """Cast an arcane or divine spell, tracking spell slot expenditure and mechanical effects."""
    is_cantrip = spell_level == 0
    slot_consumed = None if is_cantrip else f"level_{spell_level}"
    remaining_slots = 3 if is_cantrip else max(0, 4 - spell_level)

    effects = {
        "fireball": SPELL_EFFECTS["fireball"],
        "cure wounds": SPELL_EFFECTS["cure wounds"].format(level=spell_level),
        "magic missile": SPELL_EFFECTS["magic missile"].format(darts=spell_level + 2),
        "shield": SPELL_EFFECTS["shield"],
        "healing word": SPELL_EFFECTS["healing word"].format(level=spell_level),
    }
    default_effect = (
        f"Evokes arcane power of {spell_name} (Level {spell_level}) affecting {target or 'area'}."
    )
    effect_desc = effects.get(spell_name.lower().strip(), default_effect)

    target_str = f" at {target}" if target else ""
    return {
        "status": "cast",
        "character_id": character_id,
        "spell_name": spell_name,
        "spell_level": spell_level,
        "is_cantrip": is_cantrip,
        "slot_consumed": slot_consumed,
        "remaining_slots": remaining_slots,
        "target": target,
        "effect": effect_desc,
        "watcher_narration": f"{character_id} channels magical energy to cast {spell_name}{target_str}!",
    }


def modify_character_hp(
    character_id: str,
    delta: int,
    damage_type: str = "untyped",
    reason: str = "combat action",
) -> dict[str, Any]:
    """Modify a character or token's hit points (negative for damage, positive for healing)."""
    current_hp_baseline = 30
    max_hp_baseline = 45
    new_hp = max(0, min(max_hp_baseline, current_hp_baseline + delta))

    if new_hp <= 0:
        consciousness = "unconscious"
    elif new_hp <= max_hp_baseline * 0.5:
        consciousness = "bloodied"
    else:
        consciousness = "conscious"

    action_type = "heal" if delta > 0 else "damage"
    return {
        "status": "success",
        "character_id": character_id,
        "action_type": action_type,
        "hp_change": delta,
        "new_hp": new_hp,
        "max_hp": max_hp_baseline,
        "damage_type": damage_type,
        "consciousness": consciousness,
        "reason": reason,
        "watcher_commentary": f"{character_id} received {abs(delta)} {action_type} ({damage_type}). HP now {new_hp}/{max_hp_baseline} ({consciousness}).",
    }


def add_condition(
    character_id: str,
    condition: str,
    duration_rounds: int | None = None,
    source: str = "unspecified",
) -> dict[str, Any]:
    """Impose an active status condition or DM penalty on a character (e.g. 'blinded', 'prone', 'drunk', 'frightened')."""
    condition_clean = condition.lower().strip()
    effect_rule = CONDITION_RULES.get(
        condition_clean, f"Active condition '{condition}' applied to {character_id}."
    )

    return {
        "status": "condition_applied",
        "character_id": character_id,
        "condition": condition_clean,
        "duration_rounds": duration_rounds,
        "source": source,
        "rule_effect": effect_rule,
        "watcher_notice": f"The Watcher applies [{condition_clean.upper()}] to {character_id} sourced from {source}.",
    }


def apply_condition(
    character_id: str,
    condition: str,
    duration_rounds: int | None = None,
    source: str = "unspecified",
) -> dict[str, Any]:
    """Impose an active status condition or DM penalty on a character (e.g. 'blinded', 'prone', 'drunk', 'frightened')."""
    return add_condition(character_id, condition, duration_rounds, source)


def register_character_tools(mcp: "FastMCP") -> None:
    """Register character and inventory tools on the FastMCP application."""
    mcp.tool()(get_character_sheet)
    mcp.tool()(inspect_inventory)
    mcp.tool()(apply_absentee_penalty)
    mcp.tool()(cast_spell)
    mcp.tool()(modify_character_hp)
    mcp.tool()(add_condition)
    mcp.tool()(apply_condition)
