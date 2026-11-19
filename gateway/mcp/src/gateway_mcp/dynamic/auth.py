"""SpiceDB Zanzibar authorization for dynamic MCP tools (ADR-0001, ADR-0015 a).

The functions take the `PermissionChecker` port. They raise domain errors, never HTTP errors.
The admin router maps `PermissionDenied` to 403 and `AuthorizationUnavailable` to 503.
"""

from __future__ import annotations

import logging

from gateway_mcp.permissions import PermissionChecker, PermissionDenied

logger = logging.getLogger("runefoble.gateway_mcp.dynamic.auth")


async def grant_tool_permissions(
    permissions: PermissionChecker, author_id: str, tool_name: str, campaign_id: str | None = None
) -> None:
    """Write the author and campaign relationships of a dynamic tool."""
    await permissions.grant("mcp_tool", tool_name, "author", "user", author_id)
    if campaign_id:
        await permissions.grant("mcp_tool", tool_name, "campaign", "campaign", campaign_id)


async def revoke_tool_permissions(
    permissions: PermissionChecker, author_id: str, tool_name: str, campaign_id: str | None = None
) -> None:
    """Delete the author and campaign relationships of a dynamic tool.

    A failed revoke raises `AuthorizationUnavailable`, so the caller can retry.
    """
    await permissions.revoke("mcp_tool", tool_name, "author", "user", author_id)
    if campaign_id:
        await permissions.revoke("mcp_tool", tool_name, "campaign", "campaign", campaign_id)


async def check_tool_permission(
    permissions: PermissionChecker, user_id: str, tool_name: str, permission: str = "manage"
) -> bool:
    """Return whether the user holds `permission` on the dynamic tool."""
    return await permissions.check("mcp_tool", tool_name, permission, user_id)


async def enforce_tool_auth(
    permissions: PermissionChecker, user_id: str, tool_name: str, permission: str = "manage"
) -> None:
    """Raise `PermissionDenied` unless the user holds `permission` on the dynamic tool."""
    if not await check_tool_permission(permissions, user_id, tool_name, permission):
        logger.warning(
            "SpiceDB auth denied: user '%s' lacks '%s' on '%s'", user_id, permission, tool_name
        )
        raise PermissionDenied(
            f"Permission denied: user '{user_id}' lacks '{permission}' on tool '{tool_name}'"
        )
