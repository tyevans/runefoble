"""Signature builder and callable adapter for dynamic FastMCP tools."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from gateway_mcp.dynamic.models import TYPE_MAP, DynamicToolDefinition
from gateway_mcp.identity import current_caller_id
from gateway_mcp.tool_authz import ToolAuthzError, check_requirement, tool_execute

if TYPE_CHECKING:
    from gateway_mcp.dynamic.registry import DynamicToolRegistry


def make_dynamic_tool_callable(
    definition: DynamicToolDefinition, registry: DynamicToolRegistry
) -> Callable[..., Any]:
    """Construct a callable function with an inspect.Signature matching definition.parameters."""
    props = definition.parameters.get("properties", {})
    required = set(definition.parameters.get("required", []))
    param_list = [
        inspect.Parameter(
            k,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=inspect.Parameter.empty if k in required else v.get("default", None),
            annotation=TYPE_MAP.get(
                v.get("type", "string") if isinstance(v, dict) else "string", Any
            ),
        )
        for k, v in props.items()
    ]
    sig = inspect.Signature(parameters=param_list)

    async def dynamic_runner(*args: Any, **kwargs: Any) -> Any:
        ba = sig.bind(*args, **kwargs)
        ba.apply_defaults()
        caller_id = current_caller_id(registry.mcp)
        if caller_id is None:
            raise ToolAuthzError("Authentication required: the request carries no verified caller.")
        await check_requirement(caller_id, tool_execute(definition.name))
        return registry.execute_tool(definition.name, ba.arguments)

    dynamic_runner.__signature__ = sig  # type: ignore[attr-defined]
    dynamic_runner.__doc__ = definition.description
    dynamic_runner.__name__ = definition.name
    return dynamic_runner
