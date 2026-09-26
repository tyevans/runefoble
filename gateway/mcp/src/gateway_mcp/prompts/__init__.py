"""FastMCP prompt templates."""

from typing import TYPE_CHECKING

from gateway_mcp.prompts.narrative import (
    dm_narrative_guidance,
    register_narrative_prompts,
    tactical_action_adviser,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

__all__ = [
    "dm_narrative_guidance",
    "register_narrative_prompts",
    "register_prompts",
    "tactical_action_adviser",
]


def register_prompts(mcp: "FastMCP") -> None:
    """Register all prompt templates onto the FastMCP server."""
    register_narrative_prompts(mcp)
