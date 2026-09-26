"""FastMCP resource providers."""

from typing import TYPE_CHECKING

from gateway_mcp.resources.session import (
    get_active_session_context,
    get_combat_encounter_state,
    get_session_state,
    register_session_resources,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

__all__ = [
    "get_active_session_context",
    "get_combat_encounter_state",
    "get_session_state",
    "register_resources",
    "register_session_resources",
]


def register_resources(mcp: "FastMCP") -> None:
    """Register all resource providers onto the FastMCP server."""
    register_session_resources(mcp)
