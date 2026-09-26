"""Model Context Protocol (MCP) Gateway Server.

Exposes Runefoble tactical tools, board state, spells, conditions,
and AI DM controls to MCP-compliant agents and LLMs.
"""

import random
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Runefoble MCP Gateway")


@mcp.tool()
def roll_dice(notation: str = "1d20", reason: str = "Action check") -> dict[str, Any]:
    """Roll tabletop dice using standard RPG notation (e.g., '1d20', '2d6+3', '3d8-1')."""
    pattern = r"(\d+)d(\d+)(?:([+-])(\d+))?"
    match = re.match(pattern, notation.strip())
    if not match:
        rolls = [random.randint(1, 20)]
        return {
            "notation": "1d20",
            "rolls": rolls,
            "modifier": 0,
            "total": sum(rolls),
            "reason": reason,
        }

    count = int(match.group(1))
    sides = int(match.group(2))
    sign = match.group(3)
    mod = int(match.group(4)) if match.group(4) else 0
    modifier = -mod if sign == "-" else mod

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    return {
        "notation": notation,
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "reason": reason,
    }


@mcp.tool()
def inspect_tactical_board(session_id: str) -> dict[str, Any]:
    """Retrieve all tokens, coordinates, and grid dimensions for the active session."""
    return {
        "session_id": session_id,
        "grid_dimensions": {"cols": 8, "rows": 8},
        "tokens": [
            {
                "id": "t1",
                "name": "Valeros",
                "class": "Fighter",
                "x": 2,
                "y": 3,
                "hp": 38,
                "max_hp": 45,
                "ai_controlled": False,
            },
            {
                "id": "t2",
                "name": "Kyra",
                "class": "Cleric",
                "x": 3,
                "y": 3,
                "hp": 28,
                "max_hp": 32,
                "ai_controlled": True,
                "penalties": ["drunk"],
            },
            {
                "id": "t3",
                "name": "Goblin Scout",
                "type": "Monstrous",
                "x": 5,
                "y": 1,
                "hp": 7,
                "max_hp": 12,
                "hostile": True,
            },
        ],
    }


@mcp.tool()
def move_board_token(session_id: str, token_id: str, to_x: int, to_y: int) -> dict[str, Any]:
    """Move a token to target coordinates (x, y) on the tactical map."""
    return {
        "status": "success",
        "session_id": session_id,
        "token_id": token_id,
        "destination": {"x": to_x, "y": to_y},
        "watcher_commentary": f"Token {token_id} moved to ({to_x}, {to_y}). Spatial vision updated.",
    }


@mcp.tool()
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


@mcp.tool()
def narrate_with_the_watcher(scene_prompt: str, player_actions: str) -> dict[str, Any]:
    """Invoke The Watcher AI Game Master to arbitrate actions and generate immersive narration."""
    return {
        "scene_prompt": scene_prompt,
        "player_actions": player_actions,
        "narration": f"The Watcher weaves fate: As {player_actions}, the stone beneath your boots trembles. Ancient glyphs ignite along the chamber ceiling.",
        "environmental_effects": ["flickering_shadows", "low_rumble"],
    }


@mcp.tool()
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
        "fireball": "Deals 8d6 fire damage in a 20-foot radius sphere. Dexterity saving throw (DC 15) for half.",
        "cure wounds": f"Heals target for {spell_level}d8 + 3 hit points on physical touch.",
        "magic missile": f"Fires {spell_level + 2} unerring darts of magical force dealing 1d4+1 force damage each.",
        "shield": "Adds +5 to AC until the start of your next turn and nullifies Magic Missile.",
        "healing word": f"Heals target for {spell_level}d4 + 3 as a bonus action up to 60 feet.",
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


@mcp.tool()
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


@mcp.tool()
def add_condition(
    character_id: str,
    condition: str,
    duration_rounds: int | None = None,
    source: str = "unspecified",
) -> dict[str, Any]:
    """Impose an active status condition or DM penalty on a character (e.g. 'blinded', 'prone', 'drunk', 'frightened')."""
    condition_clean = condition.lower().strip()
    rule_effects = {
        "blinded": "Automatically fails ability checks requiring sight. Attack rolls against have advantage, attacks have disadvantage.",
        "prone": "Movement costs extra. Attack rolls made with disadvantage. Melee attacks against have advantage.",
        "frightened": "Disadvantage on ability checks and attack rolls while source of fear is in sight. Cannot willingly move closer.",
        "drunk": "Disadvantage on finesse and perception checks. Unpredictable tactical decisions.",
        "foolishness": "Ignores cover and tactical defense. Draws enemy threat.",
        "stunned": "Incapacitated, cannot move, can speak only falteringly. Fails Strength and Dexterity saving throws.",
        "poisoned": "Disadvantage on attack rolls and ability checks.",
    }
    effect_rule = rule_effects.get(
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


@mcp.tool()
def query_encounter_state(encounter_id: str = "enc-1") -> dict[str, Any]:
    """Query current turn order, round number, active combatants, and environmental hazards."""
    return {
        "encounter_id": encounter_id,
        "round": 2,
        "active_turn": {
            "token_id": "t1",
            "character_name": "Valeros",
            "initiative_score": 19,
            "actions_remaining": {"action": 1, "bonus_action": 1, "movement_ft": 30},
        },
        "initiative_order": [
            {"token_id": "t1", "name": "Valeros", "initiative": 19, "is_active": True},
            {"token_id": "t3", "name": "Goblin Scout", "initiative": 16, "is_active": False},
            {"token_id": "t2", "name": "Kyra (AI)", "initiative": 12, "is_active": False},
        ],
        "environmental_hazards": ["crumbling_pillars", "torches_dimming"],
        "active_combatants_count": 3,
    }


@mcp.tool()
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


@mcp.tool()
def create_encounter(
    encounter_name: str,
    terrain: str = "dungeon",
    enemies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create and initialize a new tactical combat encounter with grid dimensions and enemy placements."""
    enemy_list = enemies or [
        {"name": "Goblin Warrior", "x": 6, "y": 2, "hp": 15},
        {"name": "Goblin Archer", "x": 7, "y": 1, "hp": 10},
    ]
    return {
        "status": "encounter_created",
        "encounter_id": f"enc-{random.randint(100, 999)}",
        "name": encounter_name,
        "terrain": terrain,
        "grid": {"cols": 10, "rows": 8},
        "enemies_spawned": enemy_list,
        "initial_round": 1,
        "watcher_commentary": f"A new encounter '{encounter_name}' begins in {terrain} terrain. Roll initiative!",
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
