"""The one reader for event types and event fields (TASK-0821).

Every publish, consume, and analytics path reads the event type through `event_type_of`.
An event without a type is an error. No path substitutes a placeholder name.
"""

from __future__ import annotations

from typing import Any

from runefoble_platform.errors import RunefobleError


class EventTypeMissingError(RunefobleError):
    """An event carries no event type. It cannot be published, routed, or consumed."""

    def __init__(self, subject: str) -> None:
        super().__init__(
            f"Event has no event type and cannot be routed: {subject}. "
            "Set event_type on the event, or the 'type' key of the payload.",
            {"subject": subject},
        )


def _type_of_dict(event: dict[str, Any]) -> str | None:
    raw = event.get("event_type") or event.get("type")
    if not raw and isinstance(event.get("data"), dict):
        raw = event["data"].get("event_type")
    return str(raw) if raw else None


def event_type_of(event: Any) -> str:
    """Return the event type of a domain event, a model, or a dictionary payload.

    Raise EventTypeMissingError when no type is present. Never return a placeholder.
    """
    if isinstance(event, dict):
        raw_type = _type_of_dict(event)
    else:
        raw_value = getattr(event, "event_type", None) or getattr(event, "type", None)
        raw_type = str(raw_value) if raw_value else None
    if raw_type is None:
        raise EventTypeMissingError(type(event).__name__)
    return raw_type


def event_field(event: Any, name: str, default: Any = None) -> Any:
    """Return a field from an event object or a dictionary payload.

    A dictionary is read at the top level first, then in its `data` mapping. A value of
    None counts as absent and yields `default`.
    """
    if isinstance(event, dict):
        value = event.get(name)
        if value is None and isinstance(event.get("data"), dict):
            value = event["data"].get(name)
    else:
        value = getattr(event, name, None)
    return default if value is None else value


__all__ = ["EventTypeMissingError", "event_field", "event_type_of"]
