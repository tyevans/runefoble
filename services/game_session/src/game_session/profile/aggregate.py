"""User profile aggregate: editable profile attributes for one Zitadel subject.

Keyed by the token subject. Defaults (username, email) come from the verified token at read
time, so the aggregate stores only what a user edited. Governed by ADR-0011 and ADR-0015 (a).
"""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel
from runefoble_events.user_profile import ProfileUpdated

EDITABLE_FIELDS = frozenset({"display_name", "avatar_url", "bio", "email"})


def profile_stream_id(subject: str) -> UUID:
    """Derive the aggregate ID from the Zitadel subject."""
    return uuid5(NAMESPACE_DNS, f"runefoble:user-profile:{subject}")


class UserProfileState(BaseModel):
    """Edited profile fields. A field that was never edited stays None."""

    subject: str = ""
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    email: str | None = None


class UserProfileAggregate(DeclarativeAggregate[UserProfileState]):
    """Stores the profile fields a user has edited."""

    aggregate_type = "UserProfile"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = UserProfileState()

    def update(self, subject: str, changes: dict[str, str]) -> None:
        """Apply the edited fields. An empty set emits no event."""
        unknown = set(changes) - EDITABLE_FIELDS
        if unknown:
            raise ValueError(f"Fields not editable: {sorted(unknown)}")
        if not changes:
            return
        self.create_event(ProfileUpdated, subject=subject, changes=changes)

    @handles(ProfileUpdated)
    def _on_updated(self, event: ProfileUpdated) -> None:
        self.state.subject = event.subject
        for field, value in event.changes.items():
            setattr(self.state, field, value)
