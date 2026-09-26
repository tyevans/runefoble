"""Event inspection and extraction helpers for campaign analytics."""

from __future__ import annotations

from typing import Any


def get_event_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Extract an attribute from a dictionary, nested data payload, or object."""
    if isinstance(obj, dict):
        d = obj.get("data") if isinstance(obj.get("data"), dict) else {}
        return obj.get(key) if obj.get(key) is not None else d.get(key, default)
    return getattr(obj, key, default)


def is_event_type(obj: Any, candidates: list[str]) -> bool:
    """Check if an event matches any of the candidate type names."""
    if isinstance(obj, dict):
        d = obj.get("data") if isinstance(obj.get("data"), dict) else {}
        raw = obj.get("event_type") or obj.get("type") or d.get("event_type") or ""
    else:
        raw = getattr(obj, "event_type", obj.__class__.__name__)
    et = str(raw or obj.__class__.__name__).lower()
    return any(c.lower() in et or et.endswith(c.lower()) for c in candidates)
