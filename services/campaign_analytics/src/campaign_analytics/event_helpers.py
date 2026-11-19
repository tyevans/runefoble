"""Event type matching for campaign analytics.

The type is read by the platform reader `event_type_of`. A missing type raises. It never
matches by accident.
"""

from __future__ import annotations

from typing import Any

from runefoble_platform.event_fields import event_type_of


def is_event_type(obj: Any, candidates: list[str]) -> bool:
    """Check if an event's type matches any of the candidate type names."""
    et = event_type_of(obj).lower()
    return any(c.lower() in et or et.endswith(c.lower()) for c in candidates)
