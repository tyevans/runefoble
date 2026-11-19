"""Membership use cases: invites, joining, the roster, and removal.

Invite redemption saves the invite, then the membership, then writes the SpiceDB tuple.
Every step is safe to retry: a repeated join or remove repairs a missing tuple.
"""

from __future__ import annotations

from uuid import UUID

from game_session.campaign.errors import (
    InvalidInviteError,
    OwnerNotRemovableError,
)
from game_session.campaign.invite_aggregate import (
    generate_invite_token,
    invite_expiry,
    invite_stream_id,
)
from game_session.campaign.repositories import CampaignRepositories, concurrent_update
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
from game_session.campaign.tuples import grant_member, relation_for_role, revoke_member
from game_session.profile.aggregate import UserProfileAggregate
from game_session.profile.repository import load_profile
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.aggregate_loading import load_if_exists, save_or_conflict
from runefoble_platform.event_sourcing import AggregateRepository
from runefoble_platform.models import utc_now


def _relation_key(campaign_id: str, relation: str, user_id: str) -> str:
    return f"campaign:{campaign_id}#{relation}@user:{user_id}"


async def create_invite(
    repos: CampaignRepositories, campaign_id: str, req: InviteRequest, created_by: str
) -> InviteResponse:
    cid = parse_campaign_id(campaign_id)
    await load_campaign(repos, cid)
    token = generate_invite_token()
    now = utc_now()
    expires_at = invite_expiry(req.expires_in_hours, now)
    invite = repos.invites.create_new(invite_stream_id(token))
    invite.issue(
        campaign_id=cid,
        role=req.role,
        created_by=created_by,
        expires_at=expires_at,
        max_uses=req.max_uses,
    )
    await save_or_conflict(repos.invites, invite, concurrent_update)
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
    repos: CampaignRepositories,
    spicedb: SpiceDBPort,
    token: str,
    user_id: str,
    username: str | None,
) -> JoinCampaignResponse:
    """Redeem an invite. `username` comes from the joiner's verified token."""
    invite = await load_if_exists(repos.invites, invite_stream_id(token))
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

    invite.redeem(user_id, utc_now())
    await save_or_conflict(repos.invites, invite, concurrent_update)
    memberships.add_member(user_id, invite.state.role, username)
    await save_or_conflict(repos.memberships, memberships, concurrent_update)
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
    repos: CampaignRepositories,
    profiles: AggregateRepository[UserProfileAggregate],
    campaign_id: str,
) -> list[CampaignMemberResponse]:
    """List the owner first, then every member, each with a name (see `_member_name`)."""
    cid = parse_campaign_id(campaign_id)
    campaign = await load_campaign(repos, cid)
    memberships = await load_memberships(repos, cid)
    key = str(cid)
    entries = [(campaign.state.owner_id, "owner", campaign.state.owner_username)]
    entries.extend(
        (uid, role, memberships.username_of(uid)) for uid, role in memberships.state.members.items()
    )
    return [
        _member(key, uid, role, await _member_name(profiles, uid, recorded))
        for uid, role, recorded in entries
    ]


async def _member_name(
    profiles: AggregateRepository[UserProfileAggregate], user_id: str, recorded: str | None
) -> str | None:
    """The edited profile display name, else the recorded username, else None (ADR-0015)."""
    profile = await load_profile(profiles, user_id)
    edited = profile.state.display_name
    return edited if edited is not None else recorded


def _member(campaign_id: str, user_id: str, role: str, name: str | None) -> CampaignMemberResponse:
    relation = "owner" if role == "owner" else relation_for_role(role)
    return CampaignMemberResponse(
        user_id=user_id,
        role=role,
        subject_type="user",
        zanzibar_relation=_relation_key(campaign_id, relation, user_id),
        username=name,
        character_name=None,
    )


async def remove_member(
    repos: CampaignRepositories, spicedb: SpiceDBPort, campaign_id: str, user_id: str
) -> MemberRemovedResponse:
    """Remove a member. The owner cannot be removed. Repeating the call is safe."""
    cid = parse_campaign_id(campaign_id)
    campaign = await load_campaign(repos, cid)
    if campaign.state.owner_id == user_id:
        raise OwnerNotRemovableError("The campaign owner cannot be removed")
    memberships = await load_memberships(repos, cid)
    if memberships.role_of(user_id) is not None:
        memberships.remove_member(user_id)
        await save_or_conflict(repos.memberships, memberships, concurrent_update)
    await revoke_member(spicedb, str(cid), user_id)
    return MemberRemovedResponse(campaign_id=str(cid), user_id=user_id)
