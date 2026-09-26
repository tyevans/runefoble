"""Base event infrastructure for Runefoble, built on eventsource-py."""

from typing import Any
from uuid import UUID

from eventsource.domain.event import DomainEvent
from eventsource.domain.event_registry import register_event as _orig_register_event
from pydantic import Field


def register_event(
    event_class: Any = None,
    *,
    event_type: str | None = None,
    registry: Any = None,
) -> Any:
    """Register event decorator supporting both class and positional event_type string."""
    if isinstance(event_class, str):
        return _orig_register_event(event_type=event_class, registry=registry)
    return _orig_register_event(event_class=event_class, event_type=event_type, registry=registry)


class BaseRunefobleEvent(DomainEvent):
    """Base domain event for Runefoble, inheriting from eventsource-py DomainEvent.

    Provides CloudEvent compatibility while supporting full EventStore persistence,
    versioning, causation/correlation tracking, and multi-tenant scoping.
    """

    campaign_id: UUID | None = Field(default=None, description="Campaign identifier")
    session_id: UUID | None = Field(default=None, description="Game session identifier")

    def to_cloudevent_dict(self) -> dict[str, Any]:
        """Convert domain event to standard CloudEvents 1.0 JSON format."""
        ce_type = self.event_type.lower()
        if not ce_type.startswith("runefoble."):
            ce_type = f"runefoble.{ce_type}"
        return {
            "specversion": "1.0",
            "id": str(self.event_id),
            "source": f"/runefoble/{self.aggregate_type.lower()}/{self.aggregate_id}",
            "type": ce_type,
            "time": self.occurred_at.isoformat(),
            "datacontenttype": "application/json",
            "data": self.model_dump(mode="json"),
        }
