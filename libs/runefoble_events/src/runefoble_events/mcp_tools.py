"""Domain events for dynamic runtime FastMCP tool registration and lifecycle."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.mcp_tools.dynamic_tool_registered")
class DynamicToolRegisteredEvent(BaseRunefobleEvent):
    """Emitted when a custom dynamic FastMCP tool is registered or hot-reloaded."""

    event_type: str = "runefoble.events.mcp_tools.dynamic_tool_registered"

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "DynamicTool"
    aggregate_id: UUID = Field(default_factory=uuid4)
    tool_name: str = ""
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    author_id: str | None = None
    campaign_id: UUID | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.mcp_tools.dynamic_tool_unregistered")
class DynamicToolUnregisteredEvent(BaseRunefobleEvent):
    """Emitted when a dynamic FastMCP tool is unregistered or retired."""

    event_type: str = "runefoble.events.mcp_tools.dynamic_tool_unregistered"

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "DynamicTool"
    aggregate_id: UUID = Field(default_factory=uuid4)
    tool_name: str = ""
    unregistered_by: str | None = None
    campaign_id: UUID | str | None = None


@register_event("runefoble.events.mcp_tools.dynamic_tool_invoked")
class DynamicToolInvokedEvent(BaseRunefobleEvent):
    """Emitted when a dynamic FastMCP tool is executed by an agent or user."""

    event_type: str = "runefoble.events.mcp_tools.dynamic_tool_invoked"

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "DynamicTool"
    aggregate_id: UUID = Field(default_factory=uuid4)
    tool_name: str = ""
    user_id: str | None = None
    session_id: UUID | str | None = None
    campaign_id: UUID | str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = True
    error: str | None = None
