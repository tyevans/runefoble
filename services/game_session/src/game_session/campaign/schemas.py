"""Request and response models for the campaign routes.

Shapes match the public contract in docs/how-to/manage-campaign-lifecycle-and-invites.md.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateCampaignRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    setting: str = ""
    system: str = "5e"
    cover_image_url: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    seed_initial_session: bool = True


class UpdateCampaignRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    setting: str | None = None
    system: str | None = None
    cover_image_url: str | None = None
    status: str | None = None
    settings: dict[str, Any] | None = None


class CampaignPermissionsResponse(BaseModel):
    """Per-campaign permission flags for the caller. Each flag is a SpiceDB check (TASK-0644)."""

    view: bool
    manage: bool
    invite: bool
    launch_session: bool
    assign_roles: bool


class CampaignSummaryResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    setting: str = ""
    system: str = "5e"
    status: str = "active"
    owner_id: str = ""
    role: str | None = None
    permissions: CampaignPermissionsResponse
    member_count: int = 1
    cover_image_url: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class InviteRequest(BaseModel):
    role: Literal["player", "spectator"] = "player"
    expires_in_hours: int | None = Field(default=72, ge=1)
    max_uses: int | None = Field(default=None, ge=1)


class InviteResponse(BaseModel):
    token: str
    campaign_id: str
    role: str
    invite_url: str
    expires_at: str | None = None
    created_at: str
    max_uses: int | None = None
    uses: int = 0


class JoinCampaignRequest(BaseModel):
    invite_token: str = Field(..., min_length=1)


class JoinCampaignResponse(BaseModel):
    status: str = "joined"
    campaign_id: str
    user_id: str
    role: str
    zanzibar_relation: str


class CampaignMemberResponse(BaseModel):
    user_id: str
    role: str
    subject_type: str = "user"
    zanzibar_relation: str
    username: str | None = None
    character_name: str | None = None


class MemberRemovedResponse(BaseModel):
    status: str = "member_removed"
    campaign_id: str
    user_id: str


class CreateCampaignSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    scheduled_at: str | None = None
    description: str = ""
    status: str = "lobby"


class CampaignSessionResponse(BaseModel):
    id: str
    campaign_id: str
    title: str
    status: str
    round: int = 1
    participants_count: int = 0
    scheduled_at: str | None = None
    created_at: str


class AssignRoleRequest(BaseModel):
    """Grant a campaign role. Ownership is not grantable; it moves only with campaign creation."""

    user_id: str = Field(..., min_length=1)
    role: Literal["dungeon_master", "game_master", "player", "spectator"]


class RoleAssignedResponse(BaseModel):
    status: str = "role_assigned"
    campaign_id: str
    user_id: str
    role: str
    zanzibar_relation: str


class CampaignCapabilitiesResponse(BaseModel):
    """Per-campaign capability flags for the caller, each from a SpiceDB permission check."""

    manage: bool
    run_session: bool
    play: bool
    view: bool
