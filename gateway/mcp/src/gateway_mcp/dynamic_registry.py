"""Backward-compatibility re-exports for dynamic FastMCP tool registry."""

from gateway_mcp.dynamic import (
    TYPE_MAP,
    DynamicToolDefinition,
    DynamicToolExecutionRequest,
    DynamicToolRegistry,
    dynamic_registry,
    make_dynamic_tool_callable,
    validate_parameter_schema,
)
from gateway_mcp.routers.tools_registry import router

__all__ = [
    "TYPE_MAP",
    "DynamicToolDefinition",
    "DynamicToolExecutionRequest",
    "DynamicToolRegistry",
    "dynamic_registry",
    "make_dynamic_tool_callable",
    "router",
    "validate_parameter_schema",
]
