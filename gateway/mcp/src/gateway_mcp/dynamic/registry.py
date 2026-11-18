"""Thread-safe dynamic tool registry mapping tool names to callable functions."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any

from runefoble_events.events import (
    DynamicToolInvokedEvent,
    DynamicToolRegisteredEvent,
    DynamicToolUnregisteredEvent,
)

from gateway_mcp.dynamic.builder import make_dynamic_tool_callable
from gateway_mcp.dynamic.events import safe_dispatch_event
from gateway_mcp.dynamic.handlers import evaluate_handler, validate_handler
from gateway_mcp.dynamic.models import (
    DynamicToolDefinition,
    DynamicToolRecord,
    validate_parameter_schema,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("runefoble.gateway_mcp.dynamic.registry")


class DynamicToolRegistry:
    """Thread-safe registry mapping tool names to callable async functions with JSON Schema validation."""

    def __init__(self, mcp_server: FastMCP | None = None) -> None:
        self.mcp = mcp_server
        self._tools: dict[str, DynamicToolRecord] = {}
        self._lock = threading.RLock()

    def set_mcp_server(self, mcp_server: FastMCP) -> None:
        with self._lock:
            self.mcp = mcp_server

    def register_tool(
        self, definition: DynamicToolDefinition, author_id: str | None
    ) -> DynamicToolRecord:
        """Register a tool whose author is the verified caller (TASK-0532)."""
        validate_parameter_schema(definition.parameters)
        validate_handler(definition.handler, frozenset(definition.parameters.get("properties", {})))
        record = DynamicToolRecord(**definition.model_dump(), author_id=author_id)
        with self._lock:
            self._tools[record.name] = record
            if self.mcp is not None:
                if self.mcp._tool_manager.get_tool(record.name):
                    self.mcp._tool_manager.remove_tool(record.name)
                runner = make_dynamic_tool_callable(record, self)
                self.mcp._tool_manager.add_tool(
                    runner, name=record.name, description=record.description
                )
        safe_dispatch_event(
            DynamicToolRegisteredEvent(
                tool_name=record.name,
                description=record.description,
                parameters=record.parameters,
                author_id=author_id,
                campaign_id=record.campaign_id,
                metadata=record.metadata,
            )
        )
        return record

    def update_tool(self, name: str, definition: DynamicToolDefinition) -> DynamicToolRecord:
        """Replace a tool definition. The recorded author does not change on edit."""
        with self._lock:
            existing = self._tools.get(name)
            if existing is None:
                raise KeyError(f"Dynamic tool '{name}' not found")
        definition.name = name
        return self.register_tool(definition, author_id=existing.author_id)

    def deregister_tool(self, name: str, unregistered_by: str | None = None) -> bool:
        with self._lock:
            if name not in self._tools:
                return False
            tool_def = self._tools.pop(name)
            if self.mcp is not None and self.mcp._tool_manager.get_tool(name):
                self.mcp._tool_manager.remove_tool(name)
        safe_dispatch_event(
            DynamicToolUnregisteredEvent(
                tool_name=name, unregistered_by=unregistered_by, campaign_id=tool_def.campaign_id
            )
        )
        return True

    def get_tool(self, name: str) -> DynamicToolRecord | None:
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> list[DynamicToolRecord]:
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
            return evaluate_handler(tool_def.handler, arguments)
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
