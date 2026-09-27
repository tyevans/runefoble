"""Domain events for dynamic runtime FastMCP tool registration and lifecycle."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class DynamicToolRegisteredEvent(BaseRunefobleEvent):
    """Emitted when a custom dynamic FastMCP tool is registered or hot-reloaded."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "DynamicTool"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "DynamicToolRegistered"
    tool_name: str = ""
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    author_id: str | None = None
    campaign_id: UUID | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event
class DynamicToolUnregisteredEvent(BaseRunefobleEvent):
    """Emitted when a dynamic FastMCP tool is unregistered or retired."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "DynamicTool"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "DynamicToolUnregistered"
    tool_name: str = ""
    unregistered_by: str | None = None
    campaign_id: UUID | str | None = None


@register_event
class DynamicToolInvokedEvent(BaseRunefobleEvent):
    """Emitted when a dynamic FastMCP tool is executed by an agent or user."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "DynamicTool"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "DynamicToolInvoked"
    tool_name: str = ""
    user_id: str | None = None
    session_id: UUID | str | None = None
    campaign_id: UUID | str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = True
    error: str | None = None


# Aliases
DynamicToolRegistered = DynamicToolRegisteredEvent
DynamicToolUnregistered = DynamicToolUnregisteredEvent
DynamicToolInvoked = DynamicToolInvokedEvent
