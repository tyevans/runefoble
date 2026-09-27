"""Thread-safe dynamic tool registry mapping tool names to callable functions."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

from gateway_mcp.dynamic.builder import make_dynamic_tool_callable
from gateway_mcp.dynamic.events import safe_dispatch_event
from gateway_mcp.dynamic.models import DynamicToolDefinition, validate_parameter_schema
from gateway_mcp.sandbox import execute_sandboxed_handler, validate_sandbox_code
from runefoble_events.mcp_tools import (
    DynamicToolInvokedEvent,
    DynamicToolRegisteredEvent,
    DynamicToolUnregisteredEvent,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("runefoble.gateway_mcp.dynamic.registry")


class DynamicToolRegistry:
    """Thread-safe registry mapping tool names to callable async functions with JSON Schema validation."""

    def __init__(self, mcp_server: FastMCP | None = None) -> None:
        self.mcp = mcp_server
        self._tools: dict[str, DynamicToolDefinition] = {}
        self._lock = threading.RLock()

    def set_mcp_server(self, mcp_server: FastMCP) -> None:
        with self._lock:
            self.mcp = mcp_server

    def register_tool(
        self, definition: DynamicToolDefinition, user_id: str | None = None
    ) -> DynamicToolDefinition:
        validate_parameter_schema(definition.parameters)
        if definition.handler_code:
            validate_sandbox_code(definition.handler_code)
        with self._lock:
            self._tools[definition.name] = definition
            if self.mcp is not None:
                if self.mcp.get_tool(definition.name):
                    self.mcp._tool_manager.remove_tool(definition.name)
                runner = make_dynamic_tool_callable(definition, self)
                self.mcp._tool_manager.add_tool(
                    runner, name=definition.name, description=definition.description
                )
        safe_dispatch_event(
            DynamicToolRegisteredEvent(
                tool_name=definition.name,
                description=definition.description,
                parameters=definition.parameters,
                author_id=definition.author_id or user_id,
                campaign_id=definition.campaign_id,
                metadata=definition.metadata,
            )
        )
        return definition

    def update_tool(
        self, name: str, definition: DynamicToolDefinition, user_id: str | None = None
    ) -> DynamicToolDefinition:
        with self._lock:
            if name not in self._tools:
                raise KeyError(f"Dynamic tool '{name}' not found")
        definition.name = name
        return self.register_tool(definition, user_id=user_id)

    def deregister_tool(self, name: str, user_id: str | None = None) -> bool:
        with self._lock:
            if name not in self._tools:
                return False
            tool_def = self._tools.pop(name)
            if self.mcp is not None and self.mcp.get_tool(name):
                self.mcp._tool_manager.remove_tool(name)
        safe_dispatch_event(
            DynamicToolUnregisteredEvent(
                tool_name=name, unregistered_by=user_id, campaign_id=tool_def.campaign_id
            )
        )
        return True

    def get_tool(self, name: str) -> DynamicToolDefinition | None:
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> list[DynamicToolDefinition]:
        with self._lock:
            return list(self._tools.values())

    def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> Any:
        tool_def = self.get_tool(name)
        if not tool_def:
            raise ValueError(f"Dynamic tool '{name}' not found")
        t0, success, err_msg = time.perf_counter(), True, None
        try:
            return (
                execute_sandboxed_handler(tool_def.handler_code, arguments)
                if tool_def.handler_code
                else {"status": "success", "tool": name, "executed": True, "arguments": arguments}
            )
        except Exception as exc:
            success, err_msg = False, str(exc)
            raise
        finally:
            safe_dispatch_event(
                DynamicToolInvokedEvent(
                    tool_name=name,
                    user_id=user_id,
                    session_id=session_id,
                    campaign_id=tool_def.campaign_id,
                    arguments=arguments,
                    duration_ms=(time.perf_counter() - t0) * 1000.0,
                    success=success,
                    error=err_msg,
                )
            )


dynamic_registry = DynamicToolRegistry()
