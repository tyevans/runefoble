"""User profile routes. The gateway verifies the token and forwards to game_session.

game_session owns the profile as event-sourced state (TASK-0742, ADR-0015 a and b). The
gateway holds no profile data. A failed upstream call returns the mapping in
`upstream_errors.py`: no substitute profile is returned.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from gateway_api.auth import CurrentPrincipal
from gateway_api.proxy import forward_json
from pydantic import BaseModel, ConfigDict, Field

SERVICE = "game_session"
PROFILE = "/api/v1/profile"

router = APIRouter(tags=["User Profile"])


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, alias="displayName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    bio: str | None = None
    email: str | None = None

    model_config = ConfigDict(populate_by_name=True)


@router.get("/api/v1/profile")
async def get_profile(request: Request, user: CurrentPrincipal) -> Any:
    """Read the caller's profile from game_session."""
    return await forward_json(request, service=SERVICE, method="GET", path=PROFILE)


@router.patch("/api/v1/profile")
async def update_profile(
    req: UpdateProfileRequest, request: Request, user: CurrentPrincipal
) -> Any:
    """Edit the caller's profile in game_session. Only the fields sent are changed."""
    return await forward_json(
        request,
        service=SERVICE,
        method="PATCH",
        path=PROFILE,
        json_body=req.model_dump(exclude_none=True),
    )
