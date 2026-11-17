"""Route dependencies: verified caller identity and SpiceDB campaign permission checks.

Governed by ADR-0015 decision (c) and Hard Invariant 1. Permission names come from the
campaign definition in runefoble.zed. This module never inspects roles or claims.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends
from game_session.campaign.errors import PermissionDeniedError
from game_session.dependencies import get_spicedb_client
from game_session.settlement.auth.tokens import get_zitadel_auth_service
from runefoble_auth.principal import VerifiedPrincipal, require_principal

get_campaign_principal = require_principal(get_zitadel_auth_service)
CampaignPrincipal = Annotated[VerifiedPrincipal, Depends(get_campaign_principal)]


async def check_campaign_permission(
    spicedb: Any, campaign_id: str, permission: str, user_id: str
) -> None:
    if not await spicedb.check_permission("campaign", campaign_id, permission, "user", user_id):
        raise PermissionDeniedError(
            f"Subject 'user:{user_id}' lacks '{permission}' on 'campaign:{campaign_id}'."
        )


def campaign_permission(
    permission: str,
) -> Callable[..., Awaitable[VerifiedPrincipal]]:
    """Build a dependency that requires `permission` on the `campaign_id` path parameter."""

    async def _dependency(
        campaign_id: str,
        principal: CampaignPrincipal,
    ) -> VerifiedPrincipal:
        await check_campaign_permission(
            get_spicedb_client(), campaign_id, permission, principal.user_id
        )
        return principal

    return _dependency


ViewCampaign = Annotated[VerifiedPrincipal, Depends(campaign_permission("view"))]
ManageCampaign = Annotated[VerifiedPrincipal, Depends(campaign_permission("manage"))]
RunSessionCampaign = Annotated[VerifiedPrincipal, Depends(campaign_permission("run_session"))]
