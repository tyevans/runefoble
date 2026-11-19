"""Campaign membership aggregate: player and spectator members of one campaign.

One stream per campaign. The owner is not stored here; the campaign record holds it.
Governed by ADR-0011 and ADR-0015 decision (a).
"""

from __future__ import annotations

from typing import Any

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.campaign.errors import MemberNotFoundError
from pydantic import BaseModel, Field
from runefoble_events.events import CampaignMemberAdded, CampaignMemberRemoved


class MembershipState(BaseModel):
    """Role and recorded username of every non-owner member, in join order.

    A username comes only from the member's own verified token. None means no token
    carried one.
    """

    campaign_id: str = ""
    members: dict[str, str] = Field(default_factory=dict)
    usernames: dict[str, str | None] = Field(default_factory=dict)


class MembershipAggregate(DeclarativeAggregate[MembershipState]):
    """Adds and removes campaign members."""

    aggregate_type = "CampaignMembership"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = MembershipState(campaign_id=str(aggregate_id or ""))

    def role_of(self, user_id: str) -> str | None:
        return self.state.members.get(user_id)

    def username_of(self, user_id: str) -> str | None:
        return self.state.usernames.get(user_id)

    def add_member(self, user_id: str, role: str, username: str | None = None) -> None:
        """Add a member with `role`, or change the role of a member.

        Pass `username` only from the member's own verified token. When it is None, the
        recorded username stays. The same role emits no event.
        """
        if self.role_of(user_id) == role:
            return
        recorded = username if username is not None else self.username_of(user_id)
        self.create_event(
            CampaignMemberAdded,
            campaign_id=self.aggregate_id,
            user_id=user_id,
            role=role,
            username=recorded,
        )

    def remove_member(self, user_id: str) -> None:
        if self.role_of(user_id) is None:
            raise MemberNotFoundError(f"User {user_id} is not a member of this campaign")
        self.create_event(CampaignMemberRemoved, campaign_id=self.aggregate_id, user_id=user_id)

    @handles(CampaignMemberAdded)
    def _on_added(self, event: CampaignMemberAdded) -> None:
        self.state.members[event.user_id] = event.role
        self.state.usernames[event.user_id] = event.username

    @handles(CampaignMemberRemoved)
    def _on_removed(self, event: CampaignMemberRemoved) -> None:
        self.state.members.pop(event.user_id, None)
        self.state.usernames.pop(event.user_id, None)
