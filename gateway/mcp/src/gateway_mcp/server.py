"""Model Context Protocol (MCP) Gateway Server.

Exposes Runefoble tactical tools, board state, and AI DM controls to MCP-compliant agents and LLMs.
"""

import random
import re
from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Runefoble MCP Gateway")


@mcp.tool()
def roll_dice(notation: str = "1d20", reason: str = "Action check") -> Dict[str, Any]:
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
def inspect_tactical_board(session_id: str) -> Dict[str, Any]:
    """Retrieve all tokens, coordinates, and grid dimensions for the active session."""
    return {
        "session_id": session_id,
        "grid_dimensions": {"cols": 8, "rows": 8},
        "tokens": [
            {"id": "t1", "name": "Valeros", "class": "Fighter", "x": 2, "y": 3, "ai_controlled": False},
            {"id": "t2", "name": "Kyra", "class": "Cleric", "x": 3, "y": 3, "ai_controlled": True, "penalties": ["drunk"]},
            {"id": "t3", "name": "Goblin Scout", "type": "Monstrous", "x": 5, "y": 1, "hostile": True},
        ],
    }


@mcp.tool()
def move_board_token(session_id: str, token_id: str, to_x: int, to_y: int) -> Dict[str, Any]:
    """Move a token to target coordinates (x, y) on the tactical map."""
    return {
        "status": "success",
        "session_id": session_id,
        "token_id": token_id,
        "destination": {"x": to_x, "y": to_y},
        "watcher_commentary": f"Token {token_id} moved to ({to_x}, {to_y}). Spatial vision updated.",
    }


@mcp.tool()
def apply_absentee_penalty(character_id: str, penalty_type: str, explanation: str) -> Dict[str, Any]:
    """Impose a session miss penalty (e.g. 'drunk', 'foolishness', 'cowardice') on an absent player's PC."""
    return {
        "status": "applied",
        "character_id": character_id,
        "penalty_type": penalty_type,
        "explanation": explanation,
        "watcher_rule": f"AI stand-in will now express traits of '{penalty_type}' in dialogue and combat rolls.",
    }


@mcp.tool()
def narrate_with_the_watcher(scene_prompt: str, player_actions: str) -> Dict[str, Any]:
    """Invoke The Watcher AI Game Master to arbitrate actions and generate immersive narration."""
    return {
        "scene_prompt": scene_prompt,
        "player_actions": player_actions,
        "narration": f"The Watcher weaves fate: As {player_actions}, the stone beneath your boots trembles. Ancient glyphs ignite along the chamber ceiling.",
        "environmental_effects": ["flickering_shadows", "low_rumble"],
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
