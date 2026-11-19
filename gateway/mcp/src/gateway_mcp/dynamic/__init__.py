"""Dynamic FastMCP tool hot-reloading package."""

from gateway_mcp.dynamic.auth import (
    check_tool_permission,
    enforce_tool_auth,
    grant_tool_permissions,
    revoke_tool_permissions,
)
from gateway_mcp.dynamic.builder import make_dynamic_tool_callable
from gateway_mcp.dynamic.events import get_event_bus, set_event_bus
from gateway_mcp.dynamic.models import (
    TYPE_MAP,
    DynamicToolDefinition,
    DynamicToolExecutionRequest,
    validate_parameter_schema,
)
from gateway_mcp.dynamic.registry import DynamicToolRegistry, dynamic_registry

__all__ = [
    "TYPE_MAP",
    "DynamicToolDefinition",
    "DynamicToolExecutionRequest",
    "DynamicToolRegistry",
    "check_tool_permission",
    "dynamic_registry",
    "enforce_tool_auth",
    "get_event_bus",
    "grant_tool_permissions",
    "make_dynamic_tool_callable",
    "revoke_tool_permissions",
    "set_event_bus",
    "validate_parameter_schema",
]
