"""Dynamic FastMCP Tool Registry and Management Routers.

Enables runtime registration, parameter schema validation, and deregistration
of custom FastMCP tools without server restarts.
Governed by ADR-0008 (FastMCP Gateway Architecture).
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from gateway_mcp.sandbox import execute_sandboxed_handler, validate_sandbox_code
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("runefoble.gateway_mcp.dynamic_registry")

TYPE_MAP: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


class DynamicToolDefinition(BaseModel):
    """Declarative specification for dynamically registered MCP tools."""

    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(default="", description="Functional description for LLM planning")
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="JSON Schema for input parameters",
    )
    handler_code: str | None = Field(
        default=None, description="Optional sandboxed Python handler implementation"
    )
    sandbox_policy: dict[str, Any] = Field(
        default_factory=dict, description="Custom sandbox execution constraints"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata tags, author, and version info"
    )


class DynamicToolExecutionRequest(BaseModel):
    """Payload for invoking a dynamic tool directly via administrative frontdoor."""

    arguments: dict[str, Any] = Field(default_factory=dict)


def validate_parameter_schema(schema: dict[str, Any]) -> None:
    """Validate that parameters conform to valid JSON Schema Draft-07."""
    if not isinstance(schema, dict):
        raise ValueError("Tool parameters must be a JSON Schema dictionary")
    if schema.get("type") != "object":
        raise ValueError("Top-level parameters schema must have type 'object'")
    Draft7Validator.check_schema(schema)


def make_dynamic_tool_callable(
    definition: DynamicToolDefinition,
    registry: DynamicToolRegistry,
) -> Callable[..., Any]:
    """Construct a callable function with an inspect.Signature matching definition.parameters."""
    props = definition.parameters.get("properties", {})
    required = set(definition.parameters.get("required", []))
    param_list: list[inspect.Parameter] = []

    for p_name, p_info in props.items():
        t_name = p_info.get("type", "string") if isinstance(p_info, dict) else "string"
        ann = TYPE_MAP.get(t_name, Any)
        default_val = (
            p_info.get("default", inspect.Parameter.empty)
            if p_name in required
            else p_info.get("default", None)
        )
        param_list.append(
            inspect.Parameter(
                p_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default_val,
                annotation=ann,
            )
        )

    sig = inspect.Signature(parameters=param_list)

    async def dynamic_runner(*args: Any, **kwargs: Any) -> Any:
        ba = sig.bind(*args, **kwargs)
        ba.apply_defaults()
        return registry.execute_tool(definition.name, ba.arguments)

    dynamic_runner.__signature__ = sig
    dynamic_runner.__doc__ = definition.description
    dynamic_runner.__name__ = definition.name
    return dynamic_runner


class DynamicToolRegistry:
    """Manages runtime registration, update, and sandbox execution of dynamic FastMCP tools."""

    def __init__(self, mcp_server: FastMCP | None = None) -> None:
        self.mcp = mcp_server
        self._tools: dict[str, DynamicToolDefinition] = {}

    def set_mcp_server(self, mcp_server: FastMCP) -> None:
        self.mcp = mcp_server

    def register_tool(self, definition: DynamicToolDefinition) -> DynamicToolDefinition:
        """Register or replace a dynamic tool in the registry and FastMCP server."""
        validate_parameter_schema(definition.parameters)
        if definition.handler_code:
            validate_sandbox_code(definition.handler_code)

        self._tools[definition.name] = definition

        if self.mcp is not None:
            if self.mcp.get_tool(definition.name):
                self.mcp._tool_manager.remove_tool(definition.name)
            runner = make_dynamic_tool_callable(definition, self)
            self.mcp._tool_manager.add_tool(
                runner,
                name=definition.name,
                description=definition.description,
            )
        return definition

    def update_tool(self, name: str, definition: DynamicToolDefinition) -> DynamicToolDefinition:
        """Update an existing dynamic tool definition."""
        if name not in self._tools:
            raise KeyError(f"Dynamic tool '{name}' not found")
        definition.name = name
        return self.register_tool(definition)

    def deregister_tool(self, name: str) -> bool:
        """Remove a dynamic tool from the registry and FastMCP server."""
        if name not in self._tools:
            return False
        del self._tools[name]
        if self.mcp is not None and self.mcp.get_tool(name):
            self.mcp._tool_manager.remove_tool(name)
        return True

    def get_tool(self, name: str) -> DynamicToolDefinition | None:
        """Retrieve dynamic tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[DynamicToolDefinition]:
        """List all active dynamic tool definitions."""
        return list(self._tools.values())

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute dynamic tool in sandbox with validated arguments."""
        tool_def = self.get_tool(name)
        if not tool_def:
            raise ValueError(f"Dynamic tool '{name}' not found")
        if tool_def.handler_code:
            return execute_sandboxed_handler(tool_def.handler_code, arguments)
        return {
            "status": "success",
            "tool": name,
            "executed": True,
            "arguments": arguments,
        }


# Global registry singleton
dynamic_registry = DynamicToolRegistry()

# Administrative router exposing dynamic tool endpoints
router = APIRouter(prefix="/mcp/tools", tags=["Dynamic MCP Tools"])


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


@router.post("", response_model=dict[str, Any])
@router.post("/", response_model=dict[str, Any])
def register_dynamic_tool(payload: DynamicToolDefinition) -> dict[str, Any]:
    """Register a new dynamic tool without restarting the FastMCP gateway."""
    try:
        registered = dynamic_registry.register_tool(payload)
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
def update_dynamic_tool(name: str, payload: DynamicToolDefinition) -> dict[str, Any]:
    """Update an existing dynamic tool definition."""
    try:
        updated = dynamic_registry.update_tool(name, payload)
        return {"status": "updated", "tool": updated.model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{name}", response_model=dict[str, Any])
def deregister_dynamic_tool(name: str) -> dict[str, Any]:
    """Deregister a dynamic tool from FastMCP discovery."""
    removed = dynamic_registry.deregister_tool(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    return {"status": "deregistered", "name": name}


@router.post("/{name}/execute", response_model=dict[str, Any])
def execute_dynamic_tool(name: str, req: DynamicToolExecutionRequest) -> dict[str, Any]:
    """Execute dynamic tool in sandbox with supplied arguments."""
    try:
        result = dynamic_registry.execute_tool(name, req.arguments)
        return {"status": "success", "tool": name, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution error: {exc}") from exc
