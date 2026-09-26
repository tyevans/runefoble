"""FastMCP narrative guidance and tactical action prompts for LLMs."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def dm_narrative_guidance(scene_context: str, mood: str = "suspenseful") -> str:
    """Generate Watcher AI DM narrative guidance and environmental framing."""
    return (
        "You are The Watcher, autonomous Game Master for Runefoble.\n"
        f"Scene Context: {scene_context}\n"
        f"Atmospheric Mood: {mood}\n"
        "Provide sensory details, pacing notes, and immersive narrative descriptions for the party."
    )


def tactical_action_adviser(tactical_situation: str, character_role: str = "tactician") -> str:
    """Provide tactical analysis and combat recommendations for tabletop combat."""
    return (
        "You are the Tactical Action Adviser for Runefoble.\n"
        f"Character Role: {character_role}\n"
        f"Tactical Situation: {tactical_situation}\n"
        "Analyze token positioning, cover, spell utility, and action economy to recommend the best move."
    )


def register_narrative_prompts(mcp: "FastMCP") -> None:
    """Register narrative and tactical prompt templates on FastMCP."""
    mcp.prompt()(dm_narrative_guidance)
    mcp.prompt()(tactical_action_adviser)
