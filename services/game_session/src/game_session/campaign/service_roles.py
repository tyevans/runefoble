"""Role grants and per-campaign capability flags.

A role grant adds the member to the membership aggregate, then writes the SpiceDB relation
(ADR-0001). The caller must hold `manage` (checked by the route, not here).
"""

from __future__ import annotations

from game_session.campaign.repositories import CampaignRepositories, concurrent_update
from game_session.campaign.schemas import (
    AssignRoleRequest,
    CampaignCapabilitiesResponse,
    RoleAssignedResponse,
)
from game_session.campaign.service_campaigns import (
    load_campaign,
    load_memberships,
    parse_campaign_id,
)
from game_session.campaign.tuples import SpiceDB, grant_member, relation_for_role
from runefoble_platform.aggregate_loading import save_or_conflict

CAPABILITY_PERMISSIONS: tuple[str, ...] = ("manage", "run_session", "play", "view")


async def assign_role(
    repos: CampaignRepositories,
    spicedb: SpiceDB,
    campaign_id: str,
    req: AssignRoleRequest,
) -> RoleAssignedResponse:
    cid = parse_campaign_id(campaign_id)
    await load_campaign(repos, cid)
    memberships = await load_memberships(repos, cid)
    memberships.add_member(req.user_id, req.role)
    await save_or_conflict(repos.memberships, memberships, concurrent_update)
    await grant_member(spicedb, str(cid), req.role, req.user_id)
    relation = relation_for_role(req.role)
    return RoleAssignedResponse(
        campaign_id=str(cid),
        user_id=req.user_id,
        role=req.role,
        zanzibar_relation=f"campaign:{cid}#{relation}@user:{req.user_id}",
    )


async def capabilities(
    spicedb: SpiceDB, campaign_id: str, user_id: str
) -> CampaignCapabilitiesResponse:
    """Check each capability. Non-members receive all false."""
    flags = {
        permission: await spicedb.check_permission(
            "campaign", campaign_id, permission, "user", user_id
        )
        for permission in CAPABILITY_PERMISSIONS
    }
    return CampaignCapabilitiesResponse(**flags)
