"""SpiceDB Zanzibar authorization guard for dynamic MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from runefoble_auth.errors import AuthzError
from runefoble_auth.factory import get_spicedb_client

logger = logging.getLogger("runefoble.gateway_mcp.dynamic.auth")


def authorization_unavailable() -> HTTPException:
    """The 503 for a SpiceDB failure. A failed check or write is never a success."""
    return HTTPException(
        status_code=503,
        detail={"error": "authorization_unavailable", "message": "Authorization service failed."},
    )


async def grant_tool_permissions(
    author_id: str, tool_name: str, campaign_id: str | None = None, client: Any = None
) -> None:
    """Register SpiceDB author and campaign relationships for dynamic tool."""
    spicedb = client or get_spicedb_client()
    try:
        await spicedb.write_relationship("mcp_tool", tool_name, "author", "user", author_id)
        if campaign_id:
            await spicedb.write_relationship(
                "mcp_tool", tool_name, "campaign", "campaign", campaign_id
            )
    except AuthzError as exc:
        raise authorization_unavailable() from exc


async def revoke_tool_permissions(
    author_id: str, tool_name: str, campaign_id: str | None = None, client: Any = None
) -> None:
    """Revoke Zanzibar relationships upon dynamic tool deregistration.

    A failed revoke raises the same 503 as a failed grant, so the caller can retry.
    """
    spicedb = client or get_spicedb_client()
    try:
        await spicedb.delete_relationship("mcp_tool", tool_name, "author", "user", author_id)
        if campaign_id:
            await spicedb.delete_relationship(
                "mcp_tool", tool_name, "campaign", "campaign", campaign_id
            )
    except AuthzError as exc:
        raise authorization_unavailable() from exc


async def check_tool_permission(
    user_id: str, tool_name: str, permission: str = "manage", client: Any = None
) -> bool:
    """Check fine-grained Zanzibar permission on a dynamic tool."""
    spicedb = client or get_spicedb_client()
    try:
        return await spicedb.check_permission("mcp_tool", tool_name, permission, "user", user_id)
    except AuthzError as exc:
        raise authorization_unavailable() from exc


async def enforce_tool_auth(
    user_id: str, tool_name: str, permission: str = "manage", client: Any = None
) -> None:
    """Enforce authorization, raising HTTP 403 if permission check fails."""
    allowed = await check_tool_permission(user_id, tool_name, permission, client=client)
    if not allowed:
        logger.warning(
            "SpiceDB auth denied: user '%s' lacks '%s' on '%s'", user_id, permission, tool_name
        )
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: user '{user_id}' lacks '{permission}' on tool '{tool_name}'",
        )
