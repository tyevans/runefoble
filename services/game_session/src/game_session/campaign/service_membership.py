"""Membership use cases: invites, joining, the roster, and removal.

Invite redemption saves the invite, then the membership, then writes the SpiceDB tuple.
Every step is safe to retry: a repeated join or remove repairs a missing tuple.
"""

from __future__ import annotations

from uuid import UUID

from game_session.campaign import clock
from game_session.campaign.errors import (
    InvalidInviteError,
    OwnerNotRemovableError,
)
from game_session.campaign.invite_aggregate import (
    generate_invite_token,
    invite_expiry,
    invite_stream_id,
)
from game_session.campaign.repositories import CampaignRepositories, load_or_none, save_aggregate
from game_session.campaign.schemas import (
    CampaignMemberResponse,
    InviteRequest,
    InviteResponse,
    JoinCampaignResponse,
    MemberRemovedResponse,
)
from game_session.campaign.service_campaigns import (
    load_campaign,
    load_memberships,
    parse_campaign_id,
)
from game_session.campaign.tuples import SpiceDB, grant_member, relation_for_role, revoke_member


def display_name(user_id: str) -> str:
    """Derive a readable name from a user ID. Profile data is owned elsewhere."""
    cleaned = user_id
    for prefix in ("user-", "user_", "player-", "player_", "dm-", "dm_"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    return cleaned.replace("-", " ").replace("_", " ").title() or user_id


def _relation_key(campaign_id: str, relation: str, user_id: str) -> str:
    return f"campaign:{campaign_id}#{relation}@user:{user_id}"


async def create_invite(
    repos: CampaignRepositories, campaign_id: str, req: InviteRequest, created_by: str
) -> InviteResponse:
    cid = parse_campaign_id(campaign_id)
    await load_campaign(repos, cid)
    token = generate_invite_token()
    now = clock.utc_now()
    expires_at = invite_expiry(req.expires_in_hours, now)
    invite = repos.invites.create_new(invite_stream_id(token))
    invite.issue(
        campaign_id=cid,
        role=req.role,
        created_by=created_by,
        expires_at=expires_at,
        max_uses=req.max_uses,
    )
    await save_aggregate(repos.invites, invite)
    return InviteResponse(
        token=token,
        campaign_id=str(cid),
        role=req.role,
        invite_url=f"/#/join/{token}",
        expires_at=expires_at.isoformat() if expires_at else None,
        created_at=now.isoformat(),
        max_uses=req.max_uses,
        uses=0,
    )


async def join_campaign(
    repos: CampaignRepositories, spicedb: SpiceDB, token: str, user_id: str
) -> JoinCampaignResponse:
    invite = await load_or_none(repos.invites, invite_stream_id(token))
    if invite is None:
        raise InvalidInviteError("Invalid invite token")

    cid = UUID(invite.state.campaign_id)
    campaign = await load_campaign(repos, cid)
    campaign_key = str(cid)
    if campaign.state.owner_id == user_id:
        return _joined(campaign_key, user_id, "owner", "owner")

    memberships = await load_memberships(repos, cid)
    existing_role = memberships.role_of(user_id)
    if existing_role is not None:
        await grant_member(spicedb, campaign_key, existing_role, user_id)
        return _joined(campaign_key, user_id, existing_role, relation_for_role(existing_role))

    invite.redeem(user_id, clock.utc_now())
    await save_aggregate(repos.invites, invite)
    memberships.add_member(user_id, invite.state.role)
    await save_aggregate(repos.memberships, memberships)
    await grant_member(spicedb, campaign_key, invite.state.role, user_id)
    return _joined(campaign_key, user_id, invite.state.role, relation_for_role(invite.state.role))


def _joined(campaign_id: str, user_id: str, role: str, relation: str) -> JoinCampaignResponse:
    return JoinCampaignResponse(
        status="joined",
        campaign_id=campaign_id,
        user_id=user_id,
        role=role,
        zanzibar_relation=_relation_key(campaign_id, relation, user_id),
    )


async def list_members(
    repos: CampaignRepositories, campaign_id: str
) -> list[CampaignMemberResponse]:
    cid = parse_campaign_id(campaign_id)
    campaign = await load_campaign(repos, cid)
    memberships = await load_memberships(repos, cid)
    key = str(cid)
    owner = campaign.state.owner_id
    members = [_member(key, owner, "owner")]
    members.extend(_member(key, uid, role) for uid, role in memberships.state.members.items())
    return members


def _member(campaign_id: str, user_id: str, role: str) -> CampaignMemberResponse:
    relation = "owner" if role == "owner" else relation_for_role(role)
    return CampaignMemberResponse(
        user_id=user_id,
        role=role,
        subject_type="user",
        zanzibar_relation=_relation_key(campaign_id, relation, user_id),
        username=display_name(user_id),
        character_name=None,
    )


async def remove_member(
    repos: CampaignRepositories, spicedb: SpiceDB, campaign_id: str, user_id: str
) -> MemberRemovedResponse:
    """Remove a member. The owner cannot be removed. Repeating the call is safe."""
    cid = parse_campaign_id(campaign_id)
    campaign = await load_campaign(repos, cid)
    if campaign.state.owner_id == user_id:
        raise OwnerNotRemovableError("The campaign owner cannot be removed")
    memberships = await load_memberships(repos, cid)
    if memberships.role_of(user_id) is not None:
        memberships.remove_member(user_id)
        await save_aggregate(repos.memberships, memberships)
    await revoke_member(spicedb, str(cid), user_id)
    return MemberRemovedResponse(campaign_id=str(cid), user_id=user_id)
