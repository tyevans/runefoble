"""User profile attribute events. Owned by the game_session bounded context (ADR-0015 a).

One stream per Zitadel subject. The event carries only the fields that changed.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class ProfileUpdated(BaseRunefobleEvent):
    """Fired when a user edits profile attributes. Carries only the changed fields."""

    aggregate_type: str = "UserProfile"
    subject: str
    changes: dict[str, Any] = Field(default_factory=dict)
