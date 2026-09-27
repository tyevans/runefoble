"""SpiceDB Zanzibar authorization query projections for campaigns."""

from __future__ import annotations

from typing import Any

from gateway_api.campaign_store.models import CampaignRecord
from gateway_api.models import CampaignMemberResponse, CampaignSummaryResponse


async def get_user_campaign_role(client: Any, campaign_id: str, user_id: str) -> str | None:
    """Determine highest active Zanzibar role for user on a campaign."""
    roles = [
        ("manage", "owner"),
        ("run_session", "dungeon_master"),
        ("play", "player"),
        ("view", "spectator"),
    ]
    for action, role in roles:
        if await client.check_permission("campaign", campaign_id, action, "user", user_id):
            return role
    return None


async def build_campaign_summary(
    camp: CampaignRecord, user_id: str, client: Any
) -> CampaignSummaryResponse:
    """Construct CampaignSummaryResponse enriched with user role and member count."""
    role = await get_user_campaign_role(client, camp.id, user_id)
    rels = await client.read_relationships(resource_type="campaign", resource_id=camp.id)
    members = {r.subject_id for r in rels} | ({camp.owner_id} if camp.owner_id else set())
    return camp.to_summary(role=role, member_count=max(len(members), 1))


async def get_all_viewable_campaigns(
    user_id: str, client: Any, store: Any = None
) -> list[CampaignSummaryResponse]:
    """Retrieve and summarize all campaigns viewable by user."""
    if store is None:
        from gateway_api.campaign_store.store import campaign_store

        store = campaign_store

    try:
        for rel in await client.read_relationships(resource_type="campaign"):
            if rel.subject_id == user_id and not store.get_campaign(rel.resource_id):
                owner = user_id if rel.relation == "owner" else ""
                store.create_campaign(rel.resource_id, f"Campaign {rel.resource_id}", owner)
    except Exception:
        pass
    return [
        await build_campaign_summary(c, user_id, client)
        for c in store.list_campaigns()
        if await client.check_permission("campaign", c.id, "view", "user", user_id)
    ]


async def get_campaign_members(
    campaign_id: str, client: Any, store: Any = None
) -> list[CampaignMemberResponse]:
    """Retrieve all Zanzibar role memberships for a campaign."""
    if store is None:
        from gateway_api.campaign_store.store import campaign_store

        store = campaign_store

    rels = await client.read_relationships(resource_type="campaign", resource_id=campaign_id)
    members: list[CampaignMemberResponse] = []
    seen: set[tuple[str, str]] = set()
    valid_roles = {"owner", "dungeon_master", "game_master", "player", "spectator"}
    for r in rels:
        if r.relation in valid_roles and (r.subject_id, r.relation) not in seen:
            seen.add((r.subject_id, r.relation))
            members.append(
                CampaignMemberResponse(
                    user_id=r.subject_id,
                    role=r.relation,
                    subject_type=r.subject_type,
                    zanzibar_relation=r.to_tuple_key(),
                )
            )
    c = store.get_campaign(campaign_id)
    if c and c.owner_id and (c.owner_id, "owner") not in seen:
        members.insert(
            0,
            CampaignMemberResponse(
                user_id=c.owner_id,
                role="owner",
                subject_type="user",
                zanzibar_relation=f"campaign:{campaign_id}#owner@user:{c.owner_id}",
            ),
        )
    return members
