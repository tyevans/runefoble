"""Route dependencies: verified caller identity and SpiceDB campaign permission checks.

Governed by ADR-0015 decision (c) and Hard Invariant 1. Permission names come from the
campaign definition in runefoble.zed. This module never inspects roles or claims.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends
from game_session.campaign.errors import PermissionDeniedError
from game_session.campaign.repositories import CampaignRepositories, get_campaign_repositories
from game_session.campaign.service_campaigns import load_campaign, parse_campaign_id
from game_session.shared.identity import CallerPrincipal
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.permissions import check_subject
from runefoble_auth.principal import VerifiedPrincipal


async def check_campaign_permission(
    spicedb: Any, campaign_id: str, permission: str, user_id: str
) -> None:
    """Raise the campaign domain denial unless the user holds `permission` on the campaign."""
    if not await check_subject(spicedb, "campaign", campaign_id, permission, user_id):
        raise PermissionDeniedError(
            f"Subject 'user:{user_id}' lacks '{permission}' on 'campaign:{campaign_id}'."
        )


def campaign_permission(
    permission: str,
) -> Callable[..., Awaitable[VerifiedPrincipal]]:
    """Build a dependency that requires `permission` on the `campaign_id` path parameter.

    An unknown campaign returns 404 before any permission check, so callers can tell
    a missing campaign from one they may not see.
    """

    async def _dependency(
        campaign_id: str,
        principal: CallerPrincipal,
        repos: Annotated[CampaignRepositories, Depends(get_campaign_repositories)],
    ) -> VerifiedPrincipal:
        await load_campaign(repos, parse_campaign_id(campaign_id))
        await check_campaign_permission(
            get_spicedb_client(), campaign_id, permission, principal.user_id
        )
        return principal

    return _dependency


ViewCampaign = Annotated[VerifiedPrincipal, Depends(campaign_permission("view"))]
ManageCampaign = Annotated[VerifiedPrincipal, Depends(campaign_permission("manage"))]
RunSessionCampaign = Annotated[VerifiedPrincipal, Depends(campaign_permission("run_session"))]
