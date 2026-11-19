"""Administrative REST endpoints for dynamic FastMCP tool management.

The router takes its caller only from the verified principal dependency that the gateway
passes in (TASK-0532). No route reads an identity header or a body field. The author of a
tool is the token subject that registered it.
"""

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from runefoble_auth.principal import VerifiedPrincipal
from starlette.applications import Starlette
from starlette.routing import Mount

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


def build_tools_registry_router(
    principal_dependency: Callable[..., VerifiedPrincipal],
) -> APIRouter:
    """Build the tool routes. Every route depends on `principal_dependency` (ADR-0015 c)."""
    Caller = Annotated[VerifiedPrincipal, Depends(principal_dependency)]
    router = APIRouter(
        prefix="/mcp/tools",
        tags=["Dynamic MCP Tools"],
        dependencies=[Depends(principal_dependency)],
    )

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
        caller: Caller,
    ) -> dict[str, Any]:
        """Register a dynamic tool. A new tool's author is the caller. Replacing a tool keeps its author."""
        existing = dynamic_registry.get_tool(payload.name)
        if existing is not None:
            await enforce_tool_auth(caller.user_id, payload.name, "manage")
            author_id = existing.author_id
        else:
            author_id = caller.user_id
        try:
            registered = dynamic_registry.register_tool(payload, author_id=author_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if existing is None:
            try:
                await grant_tool_permissions(caller.user_id, payload.name, payload.campaign_id)
            except HTTPException:
                # Without an author tuple nobody could manage the tool. Undo the registration.
                dynamic_registry.deregister_tool(payload.name)
                raise
        return {"status": "registered", "tool": registered.model_dump()}

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
        caller: Caller,
    ) -> dict[str, Any]:
        """Update an existing dynamic tool definition."""
        if not dynamic_registry.get_tool(name):
            raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
        await enforce_tool_auth(caller.user_id, name, "manage")
        try:
            updated = dynamic_registry.update_tool(name, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "updated", "tool": updated.model_dump()}

    @router.delete("/{tool_name}", response_model=dict[str, Any])
    async def deregister_dynamic_tool(
        tool_name: str,
        caller: Caller,
    ) -> dict[str, Any]:
        """Revoke the author relation, then unregister the tool. A failed revoke keeps the tool (503)."""
        record = dynamic_registry.get_tool(tool_name)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        await enforce_tool_auth(caller.user_id, tool_name, "manage")
        if record.author_id is not None:
            await revoke_tool_permissions(record.author_id, tool_name, record.campaign_id)
        dynamic_registry.deregister_tool(tool_name)
        return {"status": "deregistered", "name": tool_name}

    @router.post("/{name}/execute", response_model=dict[str, Any])
    async def execute_dynamic_tool(
        name: str,
        req: DynamicToolExecutionRequest,
        caller: Caller,
    ) -> dict[str, Any]:
        """Evaluate the dynamic tool handler with supplied arguments, as the verified caller."""
        await enforce_tool_auth(caller.user_id, name, "execute")
        try:
            result = dynamic_registry.execute_tool(name, req.arguments)
            return {"status": "success", "tool": name, "result": result}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Execution error: {exc}") from exc

    return router


def mount_tools_registry(
    app: Starlette, principal_dependency: Callable[..., VerifiedPrincipal]
) -> None:
    """Serve the tool routes from the MCP ASGI app, so one process owns the registry.

    The routes sit behind every route that `app` already has, so `/mcp` and `/healthz` win.
    """
    admin = FastAPI(title="Runefoble MCP Tool Registry", docs_url=None, redoc_url=None)
    admin.include_router(build_tools_registry_router(principal_dependency))
    app.router.routes.append(Mount("/", app=admin))
