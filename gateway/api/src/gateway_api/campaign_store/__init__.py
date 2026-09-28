"""Campaign store package facade providing backward-compatible exports."""

from __future__ import annotations

from gateway_api.campaign_store.invites import (
    InviteManager,
    calculate_invite_expiry,
    format_invite_response,
    generate_invite_token,
    join_from_invite,
)
from gateway_api.campaign_store.models import (
    DEFAULT_BOARD_TOKENS,
    DEFAULT_SESSION_PARTICIPANTS,
    CampaignMemberRecord,
    CampaignRecord,
    CampaignSessionRecord,
    InviteRecord,
    InviteTokenRecord,
)
from gateway_api.campaign_store.queries import (
    build_campaign_summary,
    get_all_viewable_campaigns,
    get_campaign_members,
    get_user_campaign_role,
)
from gateway_api.campaign_store.store import CampaignStore, campaign_store

__all__ = [
    "DEFAULT_BOARD_TOKENS",
    "DEFAULT_SESSION_PARTICIPANTS",
    "CampaignMemberRecord",
    "CampaignRecord",
    "CampaignSessionRecord",
    "CampaignStore",
    "InviteManager",
    "InviteRecord",
    "InviteTokenRecord",
    "build_campaign_summary",
    "calculate_invite_expiry",
    "campaign_store",
    "format_invite_response",
    "generate_invite_token",
    "get_all_viewable_campaigns",
    "get_campaign_members",
    "get_user_campaign_role",
    "join_from_invite",
]
