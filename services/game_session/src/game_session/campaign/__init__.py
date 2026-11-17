"""Campaign lifecycle, membership, and invites owned by game_session (ADR-0015 a)."""

from game_session.campaign.errors import CampaignError, register_campaign_error_handlers
from game_session.campaign.repositories import (
    CampaignRepositories,
    build_campaign_repositories,
    get_campaign_repositories,
    set_campaign_repositories,
)
from game_session.campaign.routes import router as campaign_router

__all__ = [
    "CampaignError",
    "CampaignRepositories",
    "build_campaign_repositories",
    "campaign_router",
    "get_campaign_repositories",
    "register_campaign_error_handlers",
    "set_campaign_repositories",
]
