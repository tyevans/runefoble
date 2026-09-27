"""Administrative REST endpoints for dynamic FastMCP tool management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from gateway_mcp.dynamic.auth import (
    enforce_tool_auth,
    grant_tool_permissions,
    revoke_tool_permissions,
)
from gateway_mcp.dynamic.models import (
    DynamicToolDefinition,
    DynamicToolExecutionRequest,
)
from gateway_mcp.dynamic.registry import dynamic_registry

router = APIRouter(prefix="/mcp/tools", tags=["Dynamic MCP Tools"])


@router.get("/dynamic", response_model=dict[str, Any])
@router.get("", response_model=dict[str, Any])
@router.get("/", response_model=dict[str, Any])
def list_dynamic_tools() -> dict[str, Any]:
    """List all registered dynamic MCP tools."""
    tools = dynamic_registry.list_tools()
    return {
        "status": "success",
        "total_dynamic_tools": len(tools),
        "tools": [t.model_dump() for t in tools],
    }


@router.post("/register", response_model=dict[str, Any])
@router.post("", response_model=dict[str, Any])
@router.post("/", response_model=dict[str, Any])
async def register_dynamic_tool(
    payload: DynamicToolDefinition,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    """Register a new dynamic tool at runtime with SpiceDB authorization."""
    author_id = payload.author_id or x_user_id
    if dynamic_registry.get_tool(payload.name) is not None:
        await enforce_tool_auth(x_user_id, payload.name, "manage")
    try:
        registered = dynamic_registry.register_tool(payload, user_id=author_id)
        if author_id:
            await grant_tool_permissions(author_id, payload.name, payload.campaign_id)
        return {"status": "registered", "tool": registered.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{name}", response_model=dict[str, Any])
def get_dynamic_tool(name: str) -> dict[str, Any]:
    """Retrieve metadata and schema for a specific dynamic tool."""
    tool = dynamic_registry.get_tool(name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    return {"status": "success", "tool": tool.model_dump()}


@router.put("/{name}", response_model=dict[str, Any])
async def update_dynamic_tool(
    name: str,
    payload: DynamicToolDefinition,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    """Update an existing dynamic tool definition."""
    if not dynamic_registry.get_tool(name):
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    await enforce_tool_auth(x_user_id, name, "manage")
    try:
        updated = dynamic_registry.update_tool(name, payload, user_id=x_user_id)
        return {"status": "updated", "tool": updated.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{tool_name}", response_model=dict[str, Any])
async def deregister_dynamic_tool(
    tool_name: str,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    """Unregister a dynamic tool from FastMCP discovery."""
    if not dynamic_registry.get_tool(tool_name):
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    await enforce_tool_auth(x_user_id, tool_name, "manage")
    dynamic_registry.deregister_tool(tool_name, user_id=x_user_id)
    if x_user_id:
        await revoke_tool_permissions(x_user_id, tool_name)
    return {"status": "deregistered", "name": tool_name}


@router.post("/{name}/execute", response_model=dict[str, Any])
async def execute_dynamic_tool(
    name: str,
    req: DynamicToolExecutionRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    """Execute dynamic tool in sandbox with supplied arguments."""
    caller = req.user_id or x_user_id
    await enforce_tool_auth(caller, name, "execute")
    try:
        result = dynamic_registry.execute_tool(
            name, req.arguments, user_id=caller, session_id=req.session_id
        )
        return {"status": "success", "tool": name, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution error: {exc}") from exc
