"""Campaign lifecycle, membership, invite, and campaign session events.

Owned by the game_session bounded context (ADR-0015 decision a).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.game_session.campaign_created")
class CampaignCreated(BaseRunefobleEvent):
    """Fired when a campaign is created. The creator becomes its owner."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.campaign_created"

    aggregate_type: str = "Campaign"
    owner_id: str
    title: str
    description: str = ""
    setting: str = ""
    system: str = "5e"
    cover_image_url: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.campaign_updated")
class CampaignUpdated(BaseRunefobleEvent):
    """Fired when a campaign's editable fields change. Carries only the changed fields."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.campaign_updated"

    aggregate_type: str = "Campaign"
    changes: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.game_session.campaign_member_added")
class CampaignMemberAdded(BaseRunefobleEvent):
    """Fired when a user joins a campaign with a player or spectator role."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.campaign_member_added"

    aggregate_type: str = "CampaignMembership"
    user_id: str
    role: str


@register_event("runefoble.events.game_session.campaign_member_removed")
class CampaignMemberRemoved(BaseRunefobleEvent):
    """Fired when a member is removed from a campaign."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.campaign_member_removed"

    aggregate_type: str = "CampaignMembership"
    user_id: str


@register_event("runefoble.events.game_session.campaign_invite_created")
class CampaignInviteCreated(BaseRunefobleEvent):
    """Fired when a shareable invite is issued. The event stores no raw token."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.campaign_invite_created"

    aggregate_type: str = "CampaignInvite"
    role: str
    created_by: str
    expires_at: datetime | None = None
    max_uses: int | None = None


@register_event("runefoble.events.game_session.campaign_invite_redeemed")
class CampaignInviteRedeemed(BaseRunefobleEvent):
    """Fired when a user redeems an invite."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.campaign_invite_redeemed"

    aggregate_type: str = "CampaignInvite"
    user_id: str


@register_event("runefoble.events.game_session.campaign_session_created")
class CampaignSessionCreated(BaseRunefobleEvent):
    """Fired when a session or staging lobby is added to a campaign."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.campaign_session_created"

    aggregate_type: str = "CampaignSessions"
    session_id: str
    title: str
    status: str = "lobby"
    scheduled_at: str | None = None
    description: str = ""


__all__ = [
    "CampaignCreated",
    "CampaignInviteCreated",
    "CampaignInviteRedeemed",
    "CampaignMemberAdded",
    "CampaignMemberRemoved",
    "CampaignSessionCreated",
    "CampaignUpdated",
]
