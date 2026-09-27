"""SpiceDB Zanzibar authorization guard for dynamic MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient

logger = logging.getLogger("runefoble.gateway_mcp.dynamic.auth")
_spicedb_client: SpiceDBClient | MockSpiceDBClient | None = None


def get_spicedb_client() -> SpiceDBClient | MockSpiceDBClient:
    """Retrieve active SpiceDB client singleton with mock fallback."""
    global _spicedb_client
    if _spicedb_client is None:
        _spicedb_client = SpiceDBClient()
    return _spicedb_client


def set_spicedb_client(client: SpiceDBClient | MockSpiceDBClient | None) -> None:
    """Override SpiceDB client for unit tests and blackbox isolation."""
    global _spicedb_client
    _spicedb_client = client


async def grant_tool_permissions(
    author_id: str, tool_name: str, campaign_id: str | None = None, client: Any = None
) -> None:
    """Register SpiceDB author and campaign relationships for dynamic tool."""
    spicedb = client or get_spicedb_client()
    await spicedb.write_relationship("mcp_tool", tool_name, "author", "user", author_id)
    if campaign_id:
        await spicedb.write_relationship("mcp_tool", tool_name, "campaign", "campaign", campaign_id)


async def revoke_tool_permissions(
    author_id: str, tool_name: str, campaign_id: str | None = None, client: Any = None
) -> None:
    """Revoke Zanzibar relationships upon dynamic tool deregistration."""
    spicedb = client or get_spicedb_client()
    await spicedb.delete_relationship("mcp_tool", tool_name, "author", "user", author_id)
    if campaign_id:
        await spicedb.delete_relationship(
            "mcp_tool", tool_name, "campaign", "campaign", campaign_id
        )


async def check_tool_permission(
    user_id: str, tool_name: str, permission: str = "manage", client: Any = None
) -> bool:
    """Check fine-grained Zanzibar permission on a dynamic tool."""
    spicedb = client or get_spicedb_client()
    return await spicedb.check_permission("mcp_tool", tool_name, permission, "user", user_id)


async def enforce_tool_auth(
    user_id: str | None, tool_name: str, permission: str = "manage", client: Any = None
) -> None:
    """Enforce authorization, raising HTTP 403 if permission check fails."""
    if not user_id:
        return
    allowed = await check_tool_permission(user_id, tool_name, permission, client=client)
    if not allowed:
        logger.warning(
            "SpiceDB auth denied: user '%s' lacks '%s' on '%s'", user_id, permission, tool_name
        )
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: user '{user_id}' lacks '{permission}' on tool '{tool_name}'",
        )
