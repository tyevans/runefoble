"""Administrative REST endpoints for dynamic FastMCP tool management.

The router takes its caller only from the verified principal dependency that the gateway
passes in (TASK-0532). No route reads an identity header or a body field. The author of a
tool is the token subject that registered it. The registry and the permission port come from
the gateway container through `Depends` (TASK-0746).
"""

import logging
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from runefoble_auth.principal import VerifiedPrincipal
from starlette.applications import Starlette
from starlette.routing import Mount

from gateway_mcp.container import GatewayMcpContainer
from gateway_mcp.dynamic.auth import (
    enforce_tool_auth,
    grant_tool_permissions,
    revoke_tool_permissions,
)
from gateway_mcp.dynamic.models import (
    DynamicToolDefinition,
    DynamicToolExecutionRequest,
)
from gateway_mcp.permissions import AuthorizationUnavailable, PermissionDenied

logger = logging.getLogger("runefoble.gateway_mcp.routers.tools_registry")
EXECUTION_FAILED_DETAIL = "Dynamic tool execution failed."


def build_tools_registry_router(
    principal_dependency: Callable[..., VerifiedPrincipal],
    container_dependency: Callable[..., GatewayMcpContainer],
) -> APIRouter:
    """Build the tool routes. Every route depends on `principal_dependency` (ADR-0015 c)."""
    Caller = Annotated[VerifiedPrincipal, Depends(principal_dependency)]
    Container = Annotated[GatewayMcpContainer, Depends(container_dependency)]
    router = APIRouter(
        prefix="/mcp/tools",
        tags=["Dynamic MCP Tools"],
        dependencies=[Depends(principal_dependency)],
    )

    @router.get("/dynamic", response_model=dict[str, Any])
    def list_dynamic_tools(container: Container) -> dict[str, Any]:
        """List all registered dynamic MCP tools."""
        tools = container.registry.list_tools()
        return {
            "status": "success",
            "total_dynamic_tools": len(tools),
            "tools": [t.model_dump() for t in tools],
        }

    @router.post("/register", response_model=dict[str, Any])
    async def register_dynamic_tool(
        payload: DynamicToolDefinition,
        caller: Caller,
        container: Container,
    ) -> dict[str, Any]:
        """Register a dynamic tool. A new tool's author is the caller. Replacing a tool keeps its author."""
        registry = container.registry
        existing = registry.get_tool(payload.name)
        if existing is not None:
            await enforce_tool_auth(container.permissions, caller.user_id, payload.name, "manage")
            author_id = existing.author_id
        else:
            author_id = caller.user_id
        try:
            registered = registry.register_tool(payload, author_id=author_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if existing is None:
            try:
                await grant_tool_permissions(
                    container.permissions, caller.user_id, payload.name, payload.campaign_id
                )
            except AuthorizationUnavailable:
                # Without an author tuple nobody could manage the tool. Undo the registration.
                registry.deregister_tool(payload.name)
                raise
        return {"status": "registered", "tool": registered.model_dump()}

    @router.get("/{name}", response_model=dict[str, Any])
    def get_dynamic_tool(name: str, container: Container) -> dict[str, Any]:
        """Retrieve metadata and schema for a specific dynamic tool."""
        tool = container.registry.get_tool(name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
        return {"status": "success", "tool": tool.model_dump()}

    @router.put("/{name}", response_model=dict[str, Any])
    async def update_dynamic_tool(
        name: str,
        payload: DynamicToolDefinition,
        caller: Caller,
        container: Container,
    ) -> dict[str, Any]:
        """Update an existing dynamic tool definition."""
        if not container.registry.get_tool(name):
            raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
        await enforce_tool_auth(container.permissions, caller.user_id, name, "manage")
        try:
            updated = container.registry.update_tool(name, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "updated", "tool": updated.model_dump()}

    @router.delete("/{tool_name}", response_model=dict[str, Any])
    async def deregister_dynamic_tool(
        tool_name: str,
        caller: Caller,
        container: Container,
    ) -> dict[str, Any]:
        """Revoke the author relation, then unregister the tool. A failed revoke keeps the tool (503)."""
        record = container.registry.get_tool(tool_name)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        await enforce_tool_auth(container.permissions, caller.user_id, tool_name, "manage")
        if record.author_id is not None:
            await revoke_tool_permissions(
                container.permissions, record.author_id, tool_name, record.campaign_id
            )
        container.registry.deregister_tool(tool_name)
        return {"status": "deregistered", "name": tool_name}

    @router.post("/{name}/execute", response_model=dict[str, Any])
    async def execute_dynamic_tool(
        name: str,
        req: DynamicToolExecutionRequest,
        caller: Caller,
        container: Container,
    ) -> dict[str, Any]:
        """Evaluate the dynamic tool handler with supplied arguments, as the verified caller."""
        await enforce_tool_auth(container.permissions, caller.user_id, name, "execute")
        try:
            result = container.registry.execute_tool(name, req.arguments)
            return {"status": "success", "tool": name, "result": result}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            # The cause can hold internal state. Log it here; the caller gets a fixed detail.
            logger.exception("Dynamic tool '%s' failed to execute", name)
            raise HTTPException(status_code=500, detail=EXECUTION_FAILED_DETAIL) from exc

    return router


async def _permission_denied(_request: Request, exc: PermissionDenied) -> JSONResponse:
    """Map a denied permission to 403."""
    return JSONResponse(status_code=403, content={"detail": str(exc)})


async def _authorization_unavailable(
    _request: Request, _exc: AuthorizationUnavailable
) -> JSONResponse:
    """Map a failed authorization decision to 503. A failed check is never a success."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "error": "authorization_unavailable",
                "message": "Authorization service failed.",
            }
        },
    )


def mount_tools_registry(
    app: Starlette,
    principal_dependency: Callable[..., VerifiedPrincipal],
    container: GatewayMcpContainer,
) -> None:
    """Serve the tool routes from the MCP ASGI app, bound to one container.

    The routes sit behind every route that `app` already has, so `/mcp` and `/healthz` win.
    """
    admin = FastAPI(title="Runefoble MCP Tool Registry", docs_url=None, redoc_url=None)
    admin.add_exception_handler(PermissionDenied, _permission_denied)  # type: ignore[arg-type]
    admin.add_exception_handler(
        AuthorizationUnavailable,
        _authorization_unavailable,  # type: ignore[arg-type]
    )
    admin.include_router(build_tools_registry_router(principal_dependency, lambda: container))
    app.router.routes.append(Mount("/", app=admin))
