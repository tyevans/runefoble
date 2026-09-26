"""Model Context Protocol (MCP) Gateway Server.

Exposes Runefoble tactical tools, board state, spells, conditions,
and AI DM controls to MCP-compliant agents and LLMs.
"""

import random
import re
import time
from typing import Any

from gateway_mcp.constants import CONDITION_RULES, SPELL_EFFECTS
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Runefoble MCP Gateway")
mcp.get_tool = mcp._tool_manager.get_tool


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
    grid_cols, grid_rows = 8, 8
    if not (0 <= to_x < grid_cols and 0 <= to_y < grid_rows):
        raise ValueError(
            f"Coordinates ({to_x}, {to_y}) out of grid bounds ({grid_cols}x{grid_rows})"
        )
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


@mcp.resource("session://{session_id}/state", mime_type="application/json")
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


@mcp.tool()
async def execute_agent_action_plan(
    session_id: str, actions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Sequentially validate and execute a multi-turn agent action plan, collecting step results and timings."""
    step_results: list[dict[str, Any]] = []
    total_duration_ms: float = 0.0

    def _fail(
        err: str, idx: int, tool_name: str, duration: float = 0.0, output: Any = None
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "step": idx + 1,
            "tool": tool_name,
            "status": "error",
            "error": err,
            "duration_ms": duration,
        }
        if output is not None:
            entry["output"] = output
        step_results.append(entry)
        return {
            "status": "error",
            "success": False,
            "session_id": session_id,
            "error": err,
            "failed_step": idx + 1,
            "total_steps": len(actions),
            "completed_steps": idx,
            "steps": step_results,
            "total_duration_ms": round(total_duration_ms + duration, 2),
        }

    for idx, action in enumerate(actions):
        tool_name = action.get("tool") or action.get("name") or action.get("tool_name")
        if not tool_name:
            return _fail("Action missing 'tool' specification", idx, "unknown")

        tool = mcp._tool_manager.get_tool(tool_name)
        if tool is None:
            return _fail(f"Invalid tool: '{tool_name}' not found", idx, tool_name)

        raw = action.get("parameters") or action.get("arguments") or action.get("args")
        params = (
            dict(raw)
            if isinstance(raw, dict)
            else {
                k: v
                for k, v in action.items()
                if k not in {"tool", "name", "tool_name", "step_id", "description"}
            }
        )

        if "session_id" not in params and tool_name in {
            "move_board_token",
            "inspect_tactical_board",
        }:
            params["session_id"] = session_id

        if tool_name == "move_board_token":
            to_x, to_y = params.get("to_x"), params.get("to_y")
            if to_x is not None and to_y is not None and not (0 <= to_x < 8 and 0 <= to_y < 8):
                return _fail(
                    f"Coordinates ({to_x}, {to_y}) out of grid bounds (8x8)",
                    idx,
                    tool_name,
                )

        t0 = time.perf_counter()
        try:
            output = await tool.run(params)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            total_duration_ms += duration_ms

            if isinstance(output, dict) and output.get("status") == "error":
                return _fail(
                    output.get("error", "Step returned error status"),
                    idx,
                    tool_name,
                    duration_ms,
                    output,
                )

            step_results.append(
                {
                    "step": idx + 1,
                    "tool": tool_name,
                    "status": "success",
                    "output": output,
                    "duration_ms": duration_ms,
                }
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            return _fail(str(exc), idx, tool_name, duration_ms)

    return {
        "status": "success",
        "success": True,
        "session_id": session_id,
        "total_steps": len(actions),
        "completed_steps": len(actions),
        "steps": step_results,
        "total_duration_ms": round(total_duration_ms, 2),
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
