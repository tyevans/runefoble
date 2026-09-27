"""In-memory campaign metadata and invite token store for the Gateway API."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from gateway_api.models import (
    CampaignMemberResponse,
    CampaignSummaryResponse,
    InviteResponse,
    JoinCampaignResponse,
)


@dataclass
class CampaignRecord:
    id: str
    title: str
    description: str = ""
    setting: str = ""
    system: str = "5e"
    status: str = "active"
    owner_id: str = ""
    cover_image_url: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_summary(self, role: str | None = None, member_count: int = 1) -> CampaignSummaryResponse:
        return CampaignSummaryResponse(
            id=self.id,
            title=self.title,
            description=self.description,
            setting=self.setting,
            system=self.system,
            status=self.status,
            owner_id=self.owner_id,
            role=role,
            member_count=member_count,
            cover_image_url=self.cover_image_url,
            settings=self.settings,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "campaign_id": self.id,
            "title": self.title,
            "description": self.description,
            "setting": self.setting,
            "system": self.system,
            "status": self.status,
            "owner_id": self.owner_id,
            "cover_image_url": self.cover_image_url,
            "settings": self.settings,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class InviteRecord:
    token: str
    campaign_id: str
    role: str
    created_by: str
    expires_at: datetime | None = None
    max_uses: int | None = None
    uses: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def validate_usability(self) -> tuple[bool, str | None]:
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False, "Invite token has expired"
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False, "Invite token usage limit reached"
        return True, None


class CampaignStore:
    """Thread-safe in-memory store for campaigns and invites."""

    def __init__(self) -> None:
        self._campaigns: dict[str, CampaignRecord] = {}
        self._invites: dict[str, InviteRecord] = {}

    def create_campaign(
        self,
        campaign_id: str,
        title: str,
        owner_id: str,
        description: str = "",
        setting: str = "",
        system: str = "5e",
        cover_image_url: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> CampaignRecord:
        record = CampaignRecord(
            id=campaign_id,
            title=title,
            description=description,
            setting=setting,
            system=system,
            status="active",
            owner_id=owner_id,
            cover_image_url=cover_image_url,
            settings=settings or {},
        )
        self._campaigns[campaign_id] = record
        return record

    def get_campaign(self, campaign_id: str) -> CampaignRecord | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(self) -> list[CampaignRecord]:
        return list(self._campaigns.values())

    def update_campaign(
        self,
        campaign_id: str,
        title: str | None = None,
        description: str | None = None,
        setting: str | None = None,
        system: str | None = None,
        cover_image_url: str | None = None,
        status: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> CampaignRecord | None:
        record = self._campaigns.get(campaign_id)
        if not record:
            return None
        if title is not None:
            record.title = title
        if description is not None:
            record.description = description
        if setting is not None:
            record.setting = setting
        if system is not None:
            record.system = system
        if cover_image_url is not None:
            record.cover_image_url = cover_image_url
        if status is not None:
            record.status = status
        if settings is not None:
            record.settings = settings
        record.updated_at = datetime.now(UTC).isoformat()
        return record

    def create_from_request(self, req: Any, owner_id: str) -> tuple[str, CampaignRecord]:
        import uuid

        campaign_id = f"camp-{uuid.uuid4().hex[:8]}"
        record = self.create_campaign(
            campaign_id=campaign_id,
            title=req.title,
            owner_id=owner_id,
            description=req.description,
            setting=req.setting,
            system=req.system,
            cover_image_url=req.cover_image_url,
            settings=req.settings,
        )
        return campaign_id, record

    def update_from_request(self, campaign_id: str, req: Any, owner_id: str) -> CampaignRecord:
        camp = self.get_campaign(campaign_id)
        if not camp:
            camp = self.create_campaign(
                campaign_id=campaign_id,
                title=req.title or f"Campaign {campaign_id}",
                owner_id=owner_id,
            )
        updated = self.update_campaign(
            campaign_id=campaign_id,
            title=req.title,
            description=req.description,
            setting=req.setting,
            system=req.system,
            cover_image_url=req.cover_image_url,
            status=req.status,
            settings=req.settings,
        )
        return updated or camp

    def create_invite(
        self,
        campaign_id: str,
        role: str,
        created_by: str,
        expires_in_hours: int | None = 72,
        max_uses: int | None = None,
    ) -> InviteRecord:
        token = secrets.token_urlsafe(16)
        expires_at = (
            datetime.now(UTC) + timedelta(hours=expires_in_hours) if expires_in_hours else None
        )
        record = InviteRecord(
            token=token,
            campaign_id=campaign_id,
            role=role,
            created_by=created_by,
            expires_at=expires_at,
            max_uses=max_uses,
        )
        self._invites[token] = record
        return record

    def get_invite(self, token: str) -> InviteRecord | None:
        return self._invites.get(token)

    def use_invite(self, token: str) -> tuple[InviteRecord | None, str | None]:
        record = self._invites.get(token)
        if not record:
            return None, "Invalid invite token"
        is_valid, err = record.validate_usability()
        if not is_valid:
            return None, err
        record.uses += 1
        return record, None

    def reset(self) -> None:
        self._campaigns.clear()
        self._invites.clear()


campaign_store = CampaignStore()


async def get_user_campaign_role(client: Any, campaign_id: str, user_id: str) -> str | None:
    """Determine highest active Zanzibar role for user on a campaign."""
    if await client.check_permission("campaign", campaign_id, "manage", "user", user_id):
        return "owner"
    if await client.check_permission("campaign", campaign_id, "run_session", "user", user_id):
        return "dungeon_master"
    if await client.check_permission("campaign", campaign_id, "play", "user", user_id):
        return "player"
    if await client.check_permission("campaign", campaign_id, "view", "user", user_id):
        return "spectator"
    return None


async def build_campaign_summary(
    camp: CampaignRecord, user_id: str, client: Any
) -> CampaignSummaryResponse:
    """Construct CampaignSummaryResponse enriched with user role and member count."""
    role = await get_user_campaign_role(client, camp.id, user_id)
    rels = await client.read_relationships(resource_type="campaign", resource_id=camp.id)
    member_ids = {r.subject_id for r in rels}
    if camp.owner_id:
        member_ids.add(camp.owner_id)
    return camp.to_summary(role=role, member_count=max(len(member_ids), 1))


async def get_all_viewable_campaigns(user_id: str, client: Any) -> list[CampaignSummaryResponse]:
    """Retrieve and summarize all campaigns viewable by user."""
    try:
        user_rels = await client.read_relationships(resource_type="campaign")
        for rel in user_rels:
            if rel.subject_id == user_id and not campaign_store.get_campaign(rel.resource_id):
                owner_id = user_id if rel.relation == "owner" else ""
                campaign_store.create_campaign(
                    campaign_id=rel.resource_id,
                    title=f"Campaign {rel.resource_id}",
                    owner_id=owner_id,
                )
    except Exception:
        pass

    results: list[CampaignSummaryResponse] = []
    for camp in campaign_store.list_campaigns():
        can_view = await client.check_permission(
            resource_type="campaign",
            resource_id=camp.id,
            permission="view",
            subject_type="user",
            subject_id=user_id,
        )
        if can_view:
            summary = await build_campaign_summary(camp, user_id, client)
            results.append(summary)
    return results


async def get_campaign_members(campaign_id: str, client: Any) -> list[CampaignMemberResponse]:
    """Retrieve all Zanzibar role memberships for a campaign."""
    rels = await client.read_relationships(resource_type="campaign", resource_id=campaign_id)
    members: list[CampaignMemberResponse] = []
    seen: set[tuple[str, str]] = set()
    for rel in rels:
        if rel.relation in ("owner", "dungeon_master", "game_master", "player", "spectator"):
            key = (rel.subject_id, rel.relation)
            if key not in seen:
                seen.add(key)
                members.append(
                    CampaignMemberResponse(
                        user_id=rel.subject_id,
                        role=rel.relation,
                        subject_type=rel.subject_type,
                        zanzibar_relation=rel.to_tuple_key(),
                    )
                )
    camp = campaign_store.get_campaign(campaign_id)
    if camp and camp.owner_id and (camp.owner_id, "owner") not in seen:
        members.insert(
            0,
            CampaignMemberResponse(
                user_id=camp.owner_id,
                role="owner",
                subject_type="user",
                zanzibar_relation=f"campaign:{campaign_id}#owner@user:{camp.owner_id}",
            ),
        )
    return members


DEFAULT_SESSION_PARTICIPANTS = [
    {"username": "Alice", "character": "Valeros", "role": "player", "online": True},
    {
        "username": "Bob",
        "character": "Kyra",
        "role": "player",
        "online": False,
        "ai_stand_in": True,
    },
]

DEFAULT_BOARD_TOKENS = [
    {"id": "t1", "name": "Valeros", "x": 2, "y": 3, "color": "#2563eb"},
    {"id": "t2", "name": "Kyra", "x": 3, "y": 3, "color": "#db2777", "is_ai_controlled": True},
]


def format_invite_response(inv: InviteRecord) -> InviteResponse:
    """Format an InviteRecord into an API InviteResponse."""
    exp = inv.expires_at.isoformat() if inv.expires_at else None
    return InviteResponse(
        token=inv.token,
        campaign_id=inv.campaign_id,
        role=inv.role,
        invite_url=f"/#/join/{inv.token}",
        expires_at=exp,
        created_at=inv.created_at.isoformat(),
        max_uses=inv.max_uses,
        uses=inv.uses,
    )


async def join_from_invite(token: str, user_id: str, client: Any) -> JoinCampaignResponse:
    """Validate invite token and register user in SpiceDB."""
    from fastapi import HTTPException, status

    inv, err = campaign_store.use_invite(token)
    if err or not inv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_invite", "message": err or "Invalid invite token"},
        )
    rel = "spectator" if inv.role == "spectator" else "player"
    await client.write_relationship("campaign", inv.campaign_id, rel, "user", user_id)
    return JoinCampaignResponse(
        status="joined",
        campaign_id=inv.campaign_id,
        user_id=user_id,
        role=inv.role,
        zanzibar_relation=f"campaign:{inv.campaign_id}#{rel}@user:{user_id}",
    )
