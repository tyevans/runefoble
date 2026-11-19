"""The one adapter over FastMCP tool registration (TASK-0746).

Registration uses FastMCP's public methods. Lookup needs the tool manager, which FastMCP does
not expose publicly. This module is the only place that reads it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP


def find_tool(mcp: FastMCP, name: str) -> Any | None:
    """Return the FastMCP tool registered under `name`, or None."""
    return mcp._tool_manager.get_tool(name)


def add_tool(mcp: FastMCP, fn: Callable[..., Any], *, name: str, description: str) -> None:
    """Register `fn` as a tool called `name`."""
    mcp.add_tool(fn, name=name, description=description)


def remove_tool(mcp: FastMCP, name: str) -> None:
    """Remove the tool called `name`. The tool must be registered."""
    mcp.remove_tool(name)
