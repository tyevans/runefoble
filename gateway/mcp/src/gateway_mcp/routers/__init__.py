"""FastMCP Gateway REST Routers."""

from gateway_mcp.routers.tools_registry import (
    build_tools_registry_router,
    mount_tools_registry,
)

__all__ = ["build_tools_registry_router", "mount_tools_registry"]
